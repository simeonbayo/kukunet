# marketplace/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    Product, ProductCategory, Order, OrderItem, ProductReview,
    Promotion, ShippingMethod, Invoice, PaymentTransaction
)

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'is_active', 'created_at']
    search_fields = ['name']
    list_filter = ['is_active', 'created_at']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'product_type', 'price', 'stock_quantity', 
                   'is_in_stock_display', 'is_active']
    list_filter = ['product_type', 'is_active', 'is_featured', 'created_at']
    search_fields = ['name', 'sku', 'description']
    readonly_fields = ['sku', 'created_at', 'updated_at']
    list_editable = ['price', 'stock_quantity', 'is_active']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('tenant', 'category', 'product_type', 'name', 'sku', 
                      'description', 'short_description')
        }),
        ('Pricing', {
            'fields': ('price', 'compare_price', 'cost_price')
        }),
        ('Inventory', {
            'fields': ('stock_quantity', 'low_stock_threshold', 
                      'is_available', 'allow_backorder')
        }),
        ('Media & Shipping', {
            'fields': ('main_image', 'additional_images', 'weight_kg', 
                      'is_digital', 'requires_shipping')
        }),
        ('Status', {
            'fields': ('is_featured', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def is_in_stock_display(self, obj):
        if obj.stock_quantity > 0:
            color = 'green' if obj.stock_quantity > obj.low_stock_threshold else 'orange'
            return format_html('<span style="color: {};">✓ In Stock ({})</span>', 
                             color, obj.stock_quantity)
        return format_html('<span style="color: red;">✗ Out of Stock</span>')
    is_in_stock_display.short_description = 'Stock Status'

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'total', 'status', 'payment_status', 
                   'created_at']
    list_filter = ['status', 'payment_status', 'payment_method', 'created_at']
    search_fields = ['order_number', 'user__email', 'shipping_phone']
    readonly_fields = ['order_number', 'subtotal', 'tax', 'shipping_cost', 
                      'discount', 'total', 'created_at']
    
    actions = ['mark_as_paid', 'mark_as_shipped', 'mark_as_delivered']
    
    def mark_as_paid(self, request, queryset):
        queryset.update(status='PAID', payment_status='PAID', paid_at=timezone.now())
    mark_as_paid.short_description = "Mark selected orders as paid"
    
    def mark_as_shipped(self, request, queryset):
        queryset.update(status='SHIPPED')
    mark_as_shipped.short_description = "Mark selected orders as shipped"
    
    def mark_as_delivered(self, request, queryset):
        queryset.update(status='DELIVERED', delivered_at=timezone.now())
    mark_as_delivered.short_description = "Mark selected orders as delivered"

@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'promotion_type', 'discount_value', 
                   'is_valid_display', 'used_count']
    list_filter = ['promotion_type', 'is_active', 'start_date', 'end_date']
    search_fields = ['name', 'code']
    
    def is_valid_display(self, obj):
        if obj.is_valid:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: red;">✗ Expired</span>')
    is_valid_display.short_description = 'Status'

@admin.register(ShippingMethod)
class ShippingMethodAdmin(admin.ModelAdmin):
    list_display = ['name', 'base_cost', 'cost_per_kg', 'estimated_days_range', 'is_active']
    list_editable = ['base_cost', 'cost_per_kg', 'is_active']
    
    def estimated_days_range(self, obj):
        return f"{obj.estimated_days_min}-{obj.estimated_days_max} days"
    estimated_days_range.short_description = 'Est. Delivery'

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'order', 'invoice_date', 'due_date', 'status']
    list_filter = ['status', 'invoice_date', 'due_date']
    search_fields = ['invoice_number', 'order__order_number']

admin.site.register(ProductReview)
admin.site.register(PaymentTransaction)
admin.site.register(OrderItem)