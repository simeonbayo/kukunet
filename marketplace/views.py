# marketplace/views.py - Complete working version

from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Avg, Count, Sum, F, Q
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from decimal import Decimal
from datetime import timedelta

from .models import (
    Product, ProductCategory, Cart, CartItem, Order, OrderItem,
    ProductReview, Promotion, PaymentTransaction, ShippingMethod, Invoice
)
from .serializers import (
    ProductSerializer, ProductCategorySerializer, CartSerializer, 
    OrderSerializer, ProductReviewSerializer, PromotionSerializer,
    ShippingMethodSerializer, InvoiceSerializer
)


# marketplace/views.py - Update the ProductViewSet to include main_image

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """Public product listing for customers to browse"""
    queryset = Product.objects.filter(is_active=True, is_available=True, stock_quantity__gt=0)
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'sku']
    ordering_fields = ['price', 'created_at', 'name', 'stock_quantity']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(product_type=category)
        
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """Override to ensure main_image is included"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = serializer.data
            # Ensure image URLs are properly formatted
            for item in data:
                if item.get('main_image'):
                    # If the image path doesn't start with /media/, add it
                    if not item['main_image'].startswith('/media/') and not item['main_image'].startswith('http'):
                        item['main_image'] = f"/media/{item['main_image']}"
                # Also add image_url alias for compatibility
                item['image_url'] = item.get('main_image')
            return self.get_paginated_response(data)
        
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data
        for item in data:
            if item.get('main_image'):
                if not item['main_image'].startswith('/media/') and not item['main_image'].startswith('http'):
                    item['main_image'] = f"/media/{item['main_image']}"
            item['image_url'] = item.get('main_image')
        return Response(data)


class CartViewSet(viewsets.GenericViewSet):
    """Shopping cart management for customers"""
    queryset = Cart.objects.none()
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]
    
    def _get_cart(self, request):
        cart, created = Cart.objects.get_or_create(
            user=request.user,
            is_active=True,
            defaults={'tenant': request.user.tenant}
        )
        return cart
    
    @action(detail=False, methods=['get'])
    def view(self, request):
        """View current cart"""
        cart = self._get_cart(request)
        serializer = self.get_serializer(cart)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """Add item to cart"""
        cart = self._get_cart(request)
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))
        
        try:
            product = Product.objects.get(id=product_id, is_active=True)
            
            # Check stock
            if product.stock_quantity < quantity:
                return Response(
                    {'error': f'Only {product.stock_quantity} items available'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'price_at_add': product.price, 'quantity': quantity}
            )
            
            if not created:
                cart_item.quantity += quantity
                cart_item.save()
            
            serializer = self.get_serializer(cart)
            return Response(serializer.data)
            
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'])
    def update_item(self, request):
        """Update item quantity in cart"""
        cart = self._get_cart(request)
        item_id = request.data.get('item_id')
        quantity = int(request.data.get('quantity', 0))
        
        try:
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
            
            if quantity <= 0:
                cart_item.delete()
            else:
                if cart_item.product.stock_quantity < quantity:
                    return Response(
                        {'error': f'Only {cart_item.product.stock_quantity} items available'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                cart_item.quantity = quantity
                cart_item.save()
            
            serializer = self.get_serializer(cart)
            return Response(serializer.data)
            
        except CartItem.DoesNotExist:
            return Response({'error': 'Item not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'])
    def remove_item(self, request):
        """Remove item from cart"""
        cart = self._get_cart(request)
        item_id = request.data.get('item_id')
        
        try:
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
            cart_item.delete()
            serializer = self.get_serializer(cart)
            return Response(serializer.data)
        except CartItem.DoesNotExist:
            return Response({'error': 'Item not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'])
    def clear(self, request):
        """Clear entire cart"""
        cart = self._get_cart(request)
        cart.items.all().delete()
        return Response({'message': 'Cart cleared successfully'})
    
    # marketplace/views.py - Fix checkout to use product's tenant

    @action(detail=False, methods=['post'])
    def checkout(self, request):
        """Process checkout and create order"""
        cart = self._get_cart(request)
        
        if cart.total_items == 0:
            return Response({'error': 'Cart is empty'}, 
                        status=status.HTTP_400_BAD_REQUEST)
        
        # Validate required fields
        required_fields = ['shipping_address', 'shipping_phone']
        for field in required_fields:
            if not request.data.get(field):
                return Response({'error': f'{field} is required'}, 
                            status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # Get the tenant from the first product in cart
            # (Assuming all products belong to same agribusiness)
            first_cart_item = cart.items.filter(is_active=True).first()
            if first_cart_item:
                tenant = first_cart_item.product.tenant
            else:
                tenant = request.user.tenant
            
            # Calculate totals
            subtotal = cart.subtotal
            tax = subtotal * Decimal('0.10')
            shipping = Decimal('0.00')
            total = subtotal + tax + shipping
            
            # Create order with the product's tenant (agribusiness)
            order = Order.objects.create(
                tenant=tenant,  # Use product's tenant, not customer's tenant
                user=request.user,
                subtotal=subtotal,
                tax=tax,
                shipping_cost=shipping,
                discount=Decimal('0.00'),
                total=total,
                shipping_address=request.data.get('shipping_address'),
                shipping_city=request.data.get('shipping_city', ''),
                shipping_state=request.data.get('shipping_state', ''),
                shipping_zip=request.data.get('shipping_zip', ''),
                shipping_phone=request.data.get('shipping_phone', ''),
                payment_method=request.data.get('payment_method', 'CASH'),
                customer_notes=request.data.get('notes', '')
            )
            
            # Create order items and update stock
            for cart_item in cart.items.filter(is_active=True):
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    price=cart_item.price_at_add,
                    subtotal=cart_item.subtotal
                )
                
                # Update stock
                product = cart_item.product
                product.stock_quantity -= cart_item.quantity
                product.save()
            
            # Create invoice
            invoice = Invoice.objects.create(
                order=order,
                tenant=tenant,
                invoice_number=f"INV-{order.order_number}",
                due_date=timezone.now().date() + timedelta(days=7),
                status='SENT'
            )
            
            # Deactivate current cart and create new one
            cart.is_active = False
            cart.save()
            Cart.objects.create(user=request.user, tenant=request.user.tenant)
            
            return Response({
                'message': 'Order placed successfully',
                'order_number': order.order_number,
                'order_id': order.id,
                'total': str(order.total),
                'invoice_number': invoice.invoice_number
            }, status=status.HTTP_201_CREATED)


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """Customer order viewing"""
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or getattr(user, 'role', '') == 'ADMIN':
            return Order.objects.all()
        # Farmers see their own orders
        return Order.objects.filter(user=user)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an order"""
        order = self.get_object()
        
        if order.status not in ['PENDING', 'CONFIRMED']:
            return Response({'error': 'Order cannot be cancelled'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # Restore stock
            for item in order.items.all():
                product = item.product
                product.stock_quantity += item.quantity
                product.save()
            
            order.status = 'CANCELLED'
            order.save()
            
            if hasattr(order, 'invoice'):
                order.invoice.status = 'CANCELLED'
                order.invoice.save()
        
        return Response({'message': 'Order cancelled successfully'})
    
    @action(detail=True, methods=['get'])
    def track(self, request, pk=None):
        """Track order status"""
        order = self.get_object()
        
        tracking_info = {
            'order_number': order.order_number,
            'status': order.status,
            'created_at': order.created_at,
            'updated_at': order.updated_at,
            'estimated_delivery': (order.created_at + timedelta(days=7)).date() if order.status == 'SHIPPED' else None,
            'history': [
                {'status': 'Order Placed', 'date': order.created_at, 'description': 'Order has been placed'},
            ]
        }
        
        if order.paid_at:
            tracking_info['history'].append(
                {'status': 'Payment Confirmed', 'date': order.paid_at, 'description': 'Payment has been received'}
            )
        
        if order.status == 'SHIPPED':
            tracking_info['history'].append(
                {'status': 'Shipped', 'date': order.updated_at, 'description': 'Order has been shipped'}
            )
        elif order.status == 'DELIVERED':
            tracking_info['history'].append(
                {'status': 'Delivered', 'date': order.delivered_at, 'description': 'Order has been delivered'}
            )
        
        return Response(tracking_info)


class AdminOrderViewSet(viewsets.ModelViewSet):
    """Admin order management"""
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAdminUser]
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        order = self.get_object()
        new_status = request.data.get('status')
        admin_notes = request.data.get('admin_notes', '')
        
        if new_status not in dict(Order.ORDER_STATUS):
            return Response({'error': 'Invalid status'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        order.status = new_status
        if admin_notes:
            order.admin_notes = admin_notes
        
        if new_status == 'PAID':
            order.paid_at = timezone.now()
            order.payment_status = 'PAID'
        elif new_status == 'DELIVERED':
            order.delivered_at = timezone.now()
        
        order.save()
        
        return Response({'message': f'Order status updated to {new_status}'})


class PromotionViewSet(viewsets.ModelViewSet):
    """Promotion management"""
    queryset = Promotion.objects.all()
    serializer_class = PromotionSerializer
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def validate_code(self, request):
        code = request.query_params.get('code')
        if not code:
            return Response({'error': 'Code required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            promotion = Promotion.objects.get(
                code=code,
                is_active=True,
                start_date__lte=timezone.now(),
                end_date__gte=timezone.now()
            )
            serializer = self.get_serializer(promotion)
            return Response(serializer.data)
        except Promotion.DoesNotExist:
            return Response({'error': 'Invalid or expired code'}, 
                          status=status.HTTP_404_NOT_FOUND)


class ShippingMethodViewSet(viewsets.ReadOnlyModelViewSet):
    """Available shipping methods"""
    serializer_class = ShippingMethodSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and user.tenant:
            return ShippingMethod.objects.filter(tenant=user.tenant, is_active=True)
        return ShippingMethod.objects.filter(is_active=True)


# ==================== AGRIBUSINESS API ENDPOINTS ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def agribusiness_stats_api(request):
    """Get agribusiness dashboard statistics"""
    try:
        tenant = request.user.tenant
        if not tenant:
            return Response({
                'total_products': 0,
                'pending_orders': 0,
                'active_deliveries': 0,
                'monthly_revenue': 0,
            })
        
        total_products = Product.objects.filter(tenant=tenant).count()
        pending_orders = Order.objects.filter(tenant=tenant, status='PENDING').count()
        active_deliveries = Order.objects.filter(tenant=tenant, status='SHIPPED').count()
        
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        monthly_revenue = Order.objects.filter(
            tenant=tenant,
            created_at__date__gte=start_of_month,
            status='DELIVERED'
        ).aggregate(total=Sum('total'))['total'] or 0
        
        return Response({
            'total_products': total_products,
            'pending_orders': pending_orders,
            'active_deliveries': active_deliveries,
            'monthly_revenue': float(monthly_revenue),
        })
    except Exception as e:
        return Response({
            'total_products': 0,
            'pending_orders': 0,
            'active_deliveries': 0,
            'monthly_revenue': 0,
        })


# marketplace/views.py - Fix agribusiness_recent_orders_api

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def agribusiness_recent_orders_api(request):
    """Get recent orders for agribusiness dashboard"""
    try:
        tenant = request.user.tenant
        if not tenant:
            return Response([])
        
        recent_orders = Order.objects.filter(tenant=tenant).order_by('-created_at')[:10]
        
        orders_data = []
        for order in recent_orders:
            customer_name = 'Anonymous'
            if order.user:
                customer_name = order.user.full_name or order.user.phone_number or 'Anonymous'
            
            orders_data.append({
                'id': order.id,
                'order_number': order.order_number,
                'customer_name': customer_name,
                'total': float(order.total) if order.total else 0,
                'status': order.status,
                'created_at': order.created_at.isoformat(),
                'total_items': order.items.count()
            })
        
        return Response(orders_data)
    except Exception as e:
        print(f"Error in agribusiness_recent_orders_api: {str(e)}")
        return Response([])


# marketplace/views.py - Add debug to agribusiness_all_orders_api
# marketplace/views.py - Updated agribusiness_all_orders_api

# marketplace/views.py - Simplified agribusiness_all_orders_api

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def agribusiness_all_orders_api(request):
    """Get all orders for agribusiness with pagination"""
    try:
        tenant = request.user.tenant
        print(f"DEBUG - User: {request.user.phone_number}")
        print(f"DEBUG - Tenant: {tenant}")
        
        if not tenant:
            print("DEBUG - No tenant found")
            return Response({
                'orders': [],
                'total': 0,
                'page': 1,
                'total_pages': 0
            })
        
        # Get all orders for this tenant
        orders = Order.objects.filter(tenant=tenant).order_by('-created_at')
        print(f"DEBUG - Total orders found: {orders.count()}")
        
        # Convert to list of dictionaries
        orders_data = []
        for order in orders:
            # Get customer name safely
            customer_name = 'Anonymous'
            if order.user:
                customer_name = order.user.full_name or str(order.user.phone_number) or 'Anonymous'
            
            orders_data.append({
                'id': order.id,
                'order_number': order.order_number,
                'customer_name': customer_name,
                'customer_phone': str(order.user.phone_number) if order.user and order.user.phone_number else '',
                'total': float(order.total) if order.total else 0,
                'status': order.status,
                'created_at': order.created_at.isoformat(),
                'total_items': order.items.count()
            })
        
        # Simple pagination
        page = int(request.query_params.get('page', 1))
        page_size = 20
        start = (page - 1) * page_size
        end = start + page_size
        paginated_orders = orders_data[start:end]
        
        response_data = {
            'orders': paginated_orders,
            'total': len(orders_data),
            'page': page,
            'total_pages': (len(orders_data) + page_size - 1) // page_size if len(orders_data) > 0 else 1
        }
        
        print(f"DEBUG - Returning {len(paginated_orders)} orders")
        return Response(response_data)
        
    except Exception as e:
        print(f"DEBUG - ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response({
            'orders': [],
            'total': 0,
            'page': 1,
            'total_pages': 0
        })


# marketplace/views.py - Update agribusiness_inventory_api to return full image URLs

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def agribusiness_inventory_api(request):
    """Get inventory list for agribusiness"""
    try:
        tenant = request.user.tenant
        if not tenant:
            return Response([])
        
        search = request.query_params.get('search', '')
        
        products = Product.objects.filter(tenant=tenant)
        if search:
            products = products.filter(name__icontains=search)
        
        PRODUCT_TYPES = {
            'DAY_OLD_CHICKS': 'Day Old Chicks',
            'FEED': 'Feed',
            'GLUCOSE': 'Glucose',
            'MEDICINE': 'Medicine',
            'EQUIPMENT': 'Equipment',
            'ACCESSORIES': 'Accessories',
            'EGGS': 'Eggs',
            'MEAT': 'Meat',
            'OTHER': 'Other'
        }
        
        products_data = []
        for product in products:
            # Fix image URL to be absolute
            image_url = None
            if product.main_image:
                image_url = product.main_image
                # If it's a relative path, convert to absolute URL
                if not image_url.startswith('http') and not image_url.startswith('/media'):
                    from django.conf import settings
                    image_url = f"{settings.MEDIA_URL}{image_url}"
                    # Remove double slashes
                    image_url = image_url.replace('//', '/')
                    # Ensure it starts with /
                    if not image_url.startswith('/'):
                        image_url = f"/{image_url}"
            
            products_data.append({
                'id': product.id,
                'name': product.name,
                'category': product.product_type,
                'category_display': PRODUCT_TYPES.get(product.product_type, product.product_type),
                'price': float(product.price),
                'stock_quantity': product.stock_quantity,
                'low_stock_threshold': product.low_stock_threshold,
                'is_available': product.is_available,
                'description': product.description or '',
                'image_url': image_url
            })
        
        return Response(products_data)
    except Exception as e:
        return Response([])

# marketplace/views.py - Update agribusiness_price_list_api

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def agribusiness_price_list_api(request):
    """Get price list for agribusiness"""
    try:
        tenant = request.user.tenant
        if not tenant:
            return Response([])
        
        products = Product.objects.filter(tenant=tenant, is_active=True)
        
        PRODUCT_TYPES = {
            'DAY_OLD_CHICKS': 'Day Old Chicks',
            'FEED': 'Feed',
            'GLUCOSE': 'Glucose',
            'MEDICINE': 'Medicine',
            'EQUIPMENT': 'Equipment',
            'ACCESSORIES': 'Accessories',
            'EGGS': 'Eggs',
            'MEAT': 'Meat',
            'OTHER': 'Other'
        }
        
        products_data = []
        for product in products:
            # Fix image URL to be absolute
            image_url = None
            if product.main_image:
                image_url = product.main_image
                if not image_url.startswith('http') and not image_url.startswith('/media'):
                    from django.conf import settings
                    image_url = f"{settings.MEDIA_URL}{image_url}"
                    image_url = image_url.replace('//', '/')
                    if not image_url.startswith('/'):
                        image_url = f"/{image_url}"
            
            products_data.append({
                'id': product.id,
                'name': product.name,
                'category': product.product_type,
                'category_display': PRODUCT_TYPES.get(product.product_type, product.product_type),
                'price': float(product.price),
                'image_url': image_url
            })
        
        return Response(products_data)
    except Exception as e:
        return Response([])

# marketplace/views.py - Update the agribusiness_add_product_api function

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def agribusiness_add_product_api(request):
    """Add a new product for agribusiness with image upload"""
    try:
        tenant = request.user.tenant
        if not tenant:
            return Response({'error': 'No tenant associated'}, status=status.HTTP_400_BAD_REQUEST)
        
        name = request.data.get('name')
        if not name:
            return Response({'error': 'Product name is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get price with proper conversion
        try:
            price = Decimal(str(request.data.get('price', 0)))
        except:
            price = Decimal('0.00')
        
        stock_quantity = int(request.data.get('stock_quantity', 0))
        category = request.data.get('category', 'OTHER')
        description = request.data.get('description', '')
        
        # Handle image upload
        image = request.FILES.get('image')
        image_url = None
        
        if image:
            # Validate image type
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
            if image.content_type not in allowed_types:
                return Response({'error': 'Invalid image type. Only JPEG, PNG, GIF, and WEBP are allowed.'}, 
                              status=status.HTTP_400_BAD_REQUEST)
            
            # Validate image size (max 5MB)
            if image.size > 5 * 1024 * 1024:
                return Response({'error': 'Image size too large. Maximum 5MB allowed.'}, 
                              status=status.HTTP_400_BAD_REQUEST)
            
            # Generate unique filename
            import os
            from django.utils.text import slugify
            from datetime import datetime
            
            file_extension = os.path.splitext(image.name)[1]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            slug_name = slugify(name)[:50]
            filename = f"products/{tenant.id}/{slug_name}_{timestamp}{file_extension}"
            
            # Save the image
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile
            
            saved_path = default_storage.save(filename, ContentFile(image.read()))
            image_url = default_storage.url(saved_path)
        
        # Create product
        product = Product.objects.create(
            tenant=tenant,
            name=name,
            product_type=category,
            price=price,
            stock_quantity=stock_quantity,
            description=description,
            main_image=image_url,
            is_active=True,
            is_available=True
        )
        
        return Response({
            'message': 'Product added successfully',
            'product_id': product.id,
            'image_url': image_url
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
# marketplace/views.py - Add this endpoint for updating products

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def agribusiness_update_product_api(request, product_id):
    """Update a product"""
    try:
        product = Product.objects.get(id=product_id, tenant=request.user.tenant)
        
        name = request.data.get('name')
        if name:
            product.name = name
        
        category = request.data.get('category')
        if category:
            product.product_type = category
        
        price = request.data.get('price')
        if price:
            product.price = Decimal(str(price))
        
        stock_quantity = request.data.get('stock_quantity')
        if stock_quantity is not None:
            product.stock_quantity = int(stock_quantity)
        
        description = request.data.get('description')
        if description is not None:
            product.description = description
        
        # Handle image upload
        image = request.FILES.get('image')
        if image:
            import os
            from django.utils.text import slugify
            from datetime import datetime
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile
            
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
            if image.content_type not in allowed_types:
                return Response({'error': 'Invalid image type'}, status=status.HTTP_400_BAD_REQUEST)
            
            if image.size > 5 * 1024 * 1024:
                return Response({'error': 'Image size too large. Maximum 5MB allowed.'}, 
                              status=status.HTTP_400_BAD_REQUEST)
            
            file_extension = os.path.splitext(image.name)[1]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            slug_name = slugify(product.name)[:50]
            filename = f"products/{request.user.tenant.id}/{slug_name}_{timestamp}{file_extension}"
            
            saved_path = default_storage.save(filename, ContentFile(image.read()))
            product.main_image = default_storage.url(saved_path)
        
        product.save()
        
        return Response({
            'message': 'Product updated successfully',
            'product_id': product.id
        })
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def agribusiness_update_price_api(request, product_id):
    """Update product price"""
    try:
        product = Product.objects.get(id=product_id, tenant=request.user.tenant)
        new_price = request.data.get('price')
        
        if not new_price:
            return Response({'error': 'Price is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        product.price = Decimal(str(new_price))
        product.save()
        
        return Response({'message': 'Price updated successfully'})
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def agribusiness_restock_product_api(request, product_id):
    """Restock product"""
    try:
        product = Product.objects.get(id=product_id, tenant=request.user.tenant)
        quantity = int(request.data.get('quantity', 0))
        
        if quantity <= 0:
            return Response({'error': 'Invalid quantity'}, status=status.HTTP_400_BAD_REQUEST)
        
        product.stock_quantity += quantity
        product.save()
        
        return Response({'message': f'Added {quantity} units to stock'})
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def agribusiness_delete_product_api(request, product_id):
    """Delete a product"""
    try:
        product = Product.objects.get(id=product_id, tenant=request.user.tenant)
        product.delete()
        return Response({'message': 'Product deleted successfully'})
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def agribusiness_update_order_status_api(request, order_id):
    """Update order status"""
    try:
        order = Order.objects.get(id=order_id, tenant=request.user.tenant)
        new_status = request.data.get('status')
        
        if not new_status:
            return Response({'error': 'Status is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        order.status = new_status
        if new_status == 'DELIVERED':
            order.delivered_at = timezone.now()
        elif new_status == 'PAID':
            order.paid_at = timezone.now()
        
        order.save()
        
        return Response({'message': f'Order status updated to {new_status}'})
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
    
# marketplace/views.py - Add this class before the agribusiness API endpoints

class AgribusinessDashboardViewSet(viewsets.GenericViewSet):
    """API endpoints for agribusiness dashboard"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get dashboard statistics"""
        tenant = request.user.tenant
        if not tenant:
            return Response({
                'total_products': 0,
                'pending_orders': 0,
                'active_deliveries': 0,
                'monthly_revenue': 0,
            })
        
        total_products = Product.objects.filter(tenant=tenant).count()
        pending_orders = Order.objects.filter(tenant=tenant, status='PENDING').count()
        active_deliveries = Order.objects.filter(tenant=tenant, status='SHIPPED').count()
        
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        monthly_revenue = Order.objects.filter(
            tenant=tenant,
            created_at__date__gte=start_of_month,
            status='DELIVERED'
        ).aggregate(total=Sum('total'))['total'] or 0
        
        return Response({
            'total_products': total_products,
            'pending_orders': pending_orders,
            'active_deliveries': active_deliveries,
            'monthly_revenue': float(monthly_revenue),
        })
    
    @action(detail=False, methods=['get'])
    def recent_orders(self, request):
        """Get recent orders"""
        tenant = request.user.tenant
        if not tenant:
            return Response([])
        
        recent_orders = Order.objects.filter(tenant=tenant).order_by('-created_at')[:10]
        
        orders_data = []
        for order in recent_orders:
            customer_name = 'Anonymous'
            if order.user:
                customer_name = order.user.get_full_name() or order.user.email.split('@')[0]
            
            orders_data.append({
                'id': order.id,
                'order_number': order.order_number,
                'customer_name': customer_name,
                'total': float(order.total) if order.total else 0,
                'status': order.status,
                'created_at': order.created_at.isoformat(),
                'total_items': order.items.count()
            })
        
        return Response(orders_data)
    
    @action(detail=False, methods=['get'])
    def inventory(self, request):
        """Get inventory list"""
        tenant = request.user.tenant
        if not tenant:
            return Response([])
        
        products = Product.objects.filter(tenant=tenant)
        
        PRODUCT_TYPES = {
            'DAY_OLD_CHICKS': 'Day Old Chicks',
            'FEED': 'Feed',
            'GLUCOSE': 'Glucose',
            'MEDICINE': 'Medicine',
            'EQUIPMENT': 'Equipment',
            'ACCESSORIES': 'Accessories',
            'EGGS': 'Eggs',
            'MEAT': 'Meat',
            'OTHER': 'Other'
        }
        
        products_data = []
        for product in products:
            products_data.append({
                'id': product.id,
                'name': product.name,
                'category': product.product_type,
                'category_display': PRODUCT_TYPES.get(product.product_type, product.product_type),
                'price': float(product.price),
                'stock_quantity': product.stock_quantity,
                'low_stock_threshold': product.low_stock_threshold,
            })
        
        return Response(products_data)
    
    @action(detail=False, methods=['get'])
    def price_list(self, request):
        """Get price list"""
        tenant = request.user.tenant
        if not tenant:
            return Response([])
        
        products = Product.objects.filter(tenant=tenant, is_active=True)
        
        PRODUCT_TYPES = {
            'DAY_OLD_CHICKS': 'Day Old Chicks',
            'FEED': 'Feed',
            'GLUCOSE': 'Glucose',
            'MEDICINE': 'Medicine',
            'EQUIPMENT': 'Equipment',
            'ACCESSORIES': 'Accessories',
            'EGGS': 'Eggs',
            'MEAT': 'Meat',
            'OTHER': 'Other'
        }
        
        products_data = []
        for product in products:
            products_data.append({
                'id': product.id,
                'name': product.name,
                'category': product.product_type,
                'category_display': PRODUCT_TYPES.get(product.product_type, product.product_type),
                'price': float(product.price),
            })
        
        return Response(products_data)
    

# marketplace/views.py - Add this function with your other agribusiness API endpoints

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def agribusiness_low_stock_alerts_api(request):
    """Get products with low stock for agribusiness dashboard"""
    try:
        tenant = request.user.tenant
        if not tenant:
            return Response([])
        
        low_stock_products = Product.objects.filter(
            tenant=tenant,
            stock_quantity__lte=F('low_stock_threshold')
        ).exclude(stock_quantity=0)[:20]
        
        products_data = []
        for product in low_stock_products:
            products_data.append({
                'id': product.id,
                'name': product.name,
                'stock_quantity': product.stock_quantity,
                'min_stock': product.low_stock_threshold,
                'unit': 'units'
            })
        
        return Response(products_data)
    except Exception as e:
        return Response([])