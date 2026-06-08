# marketplace/models.py
from django.db import models
from django.conf import settings
from decimal import Decimal
from tenants.models import Tenant

class ProductCategory(models.Model):
    """Categories for marketplace products"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='product_categories',null=True, blank=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    image = models.ImageField(upload_to='categories/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Product Categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Product(models.Model):
    """Products for sale in the marketplace"""
    PRODUCT_TYPES = [
        ('DAY_OLD_CHICKS', 'Day Old Chicks'),
        ('FEED', 'Feed'),
        ('GLUCOSE', 'Glucose'),
        ('MEDICINE', 'Medicine/Vaccines'),
        ('EQUIPMENT', 'Equipment'),
        ('ACCESSORIES', 'Accessories'),
        ('EGGS', 'Eggs'),
        ('MEAT', 'Meat'),
        ('OTHER', 'Other'),
    ]
    
    created_at = models.DateTimeField(auto_now_add=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='products',null=True, blank=True)
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, related_name='products')
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES, default='OTHER')
    
    # Basic info
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=100, unique=True, blank=True)
    description = models.TextField()
    short_description = models.CharField(max_length=300, blank=True)
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Original price for discount display")
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Your cost for profit calculation",null=True, blank=True)
    
    # Inventory
    stock_quantity = models.IntegerField(default=0)
    low_stock_threshold = models.IntegerField(default=10)
    is_available = models.BooleanField(default=True)
    allow_backorder = models.BooleanField(default=False)
    
    # Media
    main_image = models.ImageField(upload_to='products/', null=True, blank=True)
    additional_images = models.JSONField(default=list, blank=True, help_text="List of additional image URLs")
    
    # Shipping
    weight_kg = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    is_digital = models.BooleanField(default=False)
    requires_shipping = models.BooleanField(default=True)
    
    # Status
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.price}"
    
    def save(self, *args, **kwargs):
        if not self.sku:
            # Generate SKU: PRODUCT_TYPE + timestamp
            prefix = self.product_type[:3].upper()
            import time
            self.sku = f"{prefix}{int(time.time())}"
        super().save(*args, **kwargs)
    
    @property
    def is_in_stock(self):
        return self.stock_quantity > 0
    
    @property
    def is_low_stock(self):
        return self.stock_quantity <= self.low_stock_threshold

class Cart(models.Model):
    """Shopping cart for users"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='carts',null=True, blank=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='carts',null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Cart for {self.user.email}"
    
    @property
    def total_items(self):
        return self.items.aggregate(total=models.Sum('quantity'))['total'] or 0
    
    @property
    def subtotal(self):
        total = 0
        for item in self.items.filter(is_active=True):
            total += item.subtotal
        return total
    
    @property
    def tax(self):
        # Assuming 10% tax, adjust as needed
        return self.subtotal * Decimal('0.10')
    
    @property
    def shipping_cost(self):
        # Implement shipping logic based on items
        return Decimal('0.00')
    
    @property
    def total(self):
        return self.subtotal + self.tax + self.shipping_cost

class CartItem(models.Model):
    """Individual items in a cart"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.IntegerField(default=1)
    price_at_add = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price when added to cart",null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['cart', 'product']
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
    
    @property
    def subtotal(self):
        return self.quantity * self.price_at_add

class Order(models.Model):
    """Customer orders"""
    ORDER_STATUS = [
        ('PENDING', 'Pending Payment'),
        ('CONFIRMED', 'Confirmed'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
        ('REFUNDED', 'Refunded'),
    ]
    
    PAYMENT_STATUS = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]
    
    PAYMENT_METHODS = [
        ('CASH', 'Cash on Delivery'),
        ('CARD', 'Credit/Debit Card'),
        ('MONEY_ORDER', 'Money Order'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('MOBILE_MONEY', 'Mobile Money'),
    ]
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='orders',null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders',null=True, blank=True)
    
    # Order info
    order_number = models.CharField(max_length=50, unique=True, blank=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='PENDING')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='PENDING')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='CASH')
    
    # Amounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True)
    
    # Shipping info
    shipping_address = models.TextField()
    shipping_city = models.CharField(max_length=100,null=True, blank=True)
    shipping_state = models.CharField(max_length=100, blank=True)
    shipping_zip = models.CharField(max_length=20, blank=True)
    shipping_phone = models.CharField(max_length=20, null=True, blank=True)
    
    # Notes
    customer_notes = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order {self.order_number} - {self.user.email}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate order number: ORD + YYYYMMDD + random
            from datetime import datetime
            import random
            date_str = datetime.now().strftime('%Y%m%d')
            random_num = random.randint(1000, 9999)
            self.order_number = f"ORD{date_str}{random_num}"
        super().save(*args, **kwargs)

class OrderItem(models.Model):
    """Individual items in an order"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items',null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='order_items',null=True, blank=True)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price at time of purchase",null=True, blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name} - Order {self.order.order_number}"

class Wishlist(models.Model):
    """User wishlist for products"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlists')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlists')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='wishlists')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'product']
    
    def __str__(self):
        return f"{self.user.email} - {self.product.name}"


# marketplace/models.py - Add these additional models

class ProductReview(models.Model):
    """Product reviews and ratings"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='product_reviews')
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    title = models.CharField(max_length=200)
    comment = models.TextField()
    images = models.JSONField(default=list, blank=True)
    is_verified_purchase = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    helpful_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['product', 'user']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.product.name} - {self.rating} stars"

class Promotion(models.Model):
    """Discount promotions and coupons"""
    PROMOTION_TYPES = [
        ('PERCENTAGE', 'Percentage Discount'),
        ('FIXED', 'Fixed Amount'),
        ('BUY_X_GET_Y', 'Buy X Get Y'),
        ('FREE_SHIPPING', 'Free Shipping'),
    ]
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='promotions')
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    promotion_type = models.CharField(max_length=20, choices=PROMOTION_TYPES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Conditions
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Applicable products/categories
    applicable_products = models.ManyToManyField(Product, blank=True, related_name='promotions')
    applicable_categories = models.ManyToManyField(ProductCategory, blank=True, related_name='promotions')
    
    # Usage limits
    usage_limit = models.IntegerField(null=True, blank=True, help_text="Total times this promo can be used")
    per_user_limit = models.IntegerField(default=1, help_text="Times per user")
    used_count = models.IntegerField(default=0)
    
    # Date range
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    @property
    def is_valid(self):
        from django.utils import timezone
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date

class PaymentTransaction(models.Model):
    """Payment transactions"""
    TRANSACTION_STATUS = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    transaction_id = models.CharField(max_length=200, unique=True)
    payment_method = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS, default='PENDING')
    
    # Payment gateway response
    gateway_response = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.transaction_id} - {self.amount}"

class ShippingMethod(models.Model):
    """Available shipping methods"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='shipping_methods')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    base_cost = models.DecimalField(max_digits=10, decimal_places=2)
    cost_per_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estimated_days_min = models.IntegerField()
    estimated_days_max = models.IntegerField()
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class Invoice(models.Model):
    """Order invoices"""
    INVOICE_STATUS = [
        ('DRAFT', 'Draft'),
        ('SENT', 'Sent'),
        ('PAID', 'Paid'),
        ('OVERDUE', 'Overdue'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='invoice')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    invoice_number = models.CharField(max_length=50, unique=True)
    invoice_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=INVOICE_STATUS, default='DRAFT')
    pdf_file = models.FileField(upload_to='invoices/', null=True, blank=True)
    
    def __str__(self):
    
        return f"Invoice {self.invoice_number} - Order {self.order.order_number}"
    

    

    

    