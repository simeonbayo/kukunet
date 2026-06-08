# marketplace/serializers.py
from rest_framework import serializers
from .models import (
    Product, ProductCategory, Cart, CartItem, Order, OrderItem,
    ProductReview, Promotion, PaymentTransaction, ShippingMethod, Invoice
)

class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ['id', 'name', 'description', 'image', 'is_active']

# marketplace/serializers.py - Make sure ProductSerializer includes main_image

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    is_in_stock = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'sku', 'product_type', 'category', 'category_name',
            'description', 'short_description', 'price', 'compare_price',
            'stock_quantity', 'is_in_stock', 'is_available', 'main_image',
            'is_featured', 'is_active', 'created_at'
        ]

class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_image = serializers.ImageField(source='product.main_image', read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_name', 'product_image', 'quantity', 'price_at_add', 'subtotal']

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_items', 'subtotal', 'tax', 'shipping_cost', 'total', 'created_at']


class ProductReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = ProductReview
        fields = ['id', 'product', 'user', 'user_name', 'rating', 'title', 
                 'comment', 'images', 'is_verified_purchase', 'helpful_count', 
                 'created_at']
        read_only_fields = ['user', 'is_verified_purchase', 'helpful_count']

class PromotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = ['id', 'name', 'code', 'promotion_type', 'discount_value',
                 'min_order_amount', 'max_discount_amount', 'is_valid']

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_image = serializers.ImageField(source='product.main_image', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'product_image', 
                 'quantity', 'price', 'subtotal']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'user', 'user_name', 'status', 'status_display',
            'payment_status', 'payment_method', 'subtotal', 'tax', 'shipping_cost',
            'discount', 'total', 'shipping_address', 'shipping_city', 'shipping_state',
            'shipping_zip', 'shipping_phone', 'items', 'created_at', 'paid_at', 'delivered_at'
        ]

class ShippingMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingMethod
        fields = '__all__'

class InvoiceSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    
    class Meta:
        model = Invoice
        fields = ['id', 'invoice_number', 'order_number', 'invoice_date', 
                 'due_date', 'status', 'pdf_file']