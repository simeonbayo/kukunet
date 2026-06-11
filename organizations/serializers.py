# organizations/serializers.py
from rest_framework import serializers
from accounts.models import User
from farm.models import FlockBatch, DailyRecord, FeedPurchase
from marketplace.models import Order, OrderItem


class FarmerSerializer(serializers.ModelSerializer):
    """Serializer for farmer users under an organization"""
    total_flocks = serializers.SerializerMethodField()
    total_birds = serializers.SerializerMethodField()
    total_spent = serializers.SerializerMethodField()
    total_earned = serializers.SerializerMethodField()
    district = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'phone_number', 'email', 'role',
            'total_flocks', 'total_birds', 'total_spent', 'total_earned',
            'is_active', 'registered_date', 'district', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_total_flocks(self, obj):
        return FlockBatch.objects.filter(farmer=obj, tenant=obj.tenant).count()
    
    def get_total_birds(self, obj):
        result = FlockBatch.objects.filter(farmer=obj, tenant=obj.tenant).aggregate(
            total=serializers.models.Sum('current_quantity')
        )
        return result['total'] or 0
    
    def get_total_spent(self, obj):
        result = DailyRecord.objects.filter(
            batch__farmer=obj,
            tenant=obj.tenant
        ).aggregate(total=serializers.models.Sum('total_expenses'))
        return float(result['total'] or 0)
    
    def get_total_earned(self, obj):
        result = DailyRecord.objects.filter(
            batch__farmer=obj,
            tenant=obj.tenant
        ).aggregate(total=serializers.models.Sum('sales_revenue'))
        return float(result['total'] or 0)
    
    def get_district(self, obj):
        if hasattr(obj, 'profile') and obj.profile:
            return obj.profile.district
        return ''


class FarmerDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for a single farmer"""
    flocks = serializers.SerializerMethodField()
    recent_records = serializers.SerializerMethodField()
    financial_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'phone_number', 'email', 'role',
            'is_active', 'created_at', 'flocks', 'recent_records', 'financial_summary'
        ]
    
    def get_flocks(self, obj):
        flocks = FlockBatch.objects.filter(farmer=obj, tenant=obj.tenant)
        return FlockBatchSerializer(flocks, many=True).data
    
    def get_recent_records(self, obj):
        records = DailyRecord.objects.filter(
            batch__farmer=obj,
            tenant=obj.tenant
        ).order_by('-date')[:30]
        return DailyRecordSerializer(records, many=True).data
    
    def get_financial_summary(self, obj):
        records = DailyRecord.objects.filter(batch__farmer=obj, tenant=obj.tenant)
        total_revenue = records.aggregate(total=serializers.models.Sum('sales_revenue'))['total'] or 0
        total_expenses = records.aggregate(total=serializers.models.Sum('total_expenses'))['total'] or 0
        return {
            'total_revenue': float(total_revenue),
            'total_expenses': float(total_expenses),
            'net_profit': float(total_revenue - total_expenses)
        }


class FlockBatchSerializer(serializers.ModelSerializer):
    """Serializer for flock batches"""
    farmer_name = serializers.CharField(source='farmer.full_name', read_only=True)
    farm_name = serializers.CharField(source='farm.farm_name', read_only=True)
    house_name = serializers.CharField(source='house.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    bird_type_display = serializers.CharField(source='get_bird_type_display', read_only=True)
    breed_display = serializers.CharField(source='get_breed_display', read_only=True)
    mortality_rate = serializers.SerializerMethodField()
    survival_rate = serializers.SerializerMethodField()
    total_feed_consumed = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_eggs_produced = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = FlockBatch
        fields = [
            'id', 'batch_number', 'batch_name', 'farmer', 'farmer_name',
            'farm', 'farm_name', 'house', 'house_name', 'bird_type',
            'bird_type_display', 'breed', 'breed_display', 'initial_quantity',
            'current_quantity', 'status', 'status_display', 'start_date',
            'expected_end_date', 'end_date', 'age_days', 'age_weeks',
            'mortality_rate', 'survival_rate', 'total_feed_consumed',
            'total_eggs_produced', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'batch_number']
    
    def get_mortality_rate(self, obj):
        if obj.initial_quantity > 0:
            return round((obj.total_mortality / obj.initial_quantity) * 100, 2)
        return 0
    
    def get_survival_rate(self, obj):
        if obj.initial_quantity > 0:
            return round((obj.current_quantity / obj.initial_quantity) * 100, 2)
        return 0


class DailyRecordSerializer(serializers.ModelSerializer):
    """Serializer for daily records"""
    farmer_name = serializers.CharField(source='batch.farmer.full_name', read_only=True)
    batch_name = serializers.CharField(source='batch.batch_name', read_only=True)
    health_status_display = serializers.CharField(source='get_health_status_display', read_only=True)
    litter_condition_display = serializers.CharField(source='get_litter_condition_display', read_only=True)
    profit = serializers.SerializerMethodField()
    
    class Meta:
        model = DailyRecord
        fields = [
            'id', 'date', 'batch', 'batch_name', 'farmer_name',
            'opening_bird_count', 'birds_added', 'mortality', 'birds_sold',
            'birds_culled', 'closing_bird_count', 'feed_type',
            'feed_given_kg', 'feed_consumed_kg', 'feed_cost',
            'water_provided_liters', 'water_consumed_liters',
            'health_status', 'health_status_display', 'signs_observed',
            'treatments_given', 'medication_cost', 'vaccine_cost',
            'labour_cost', 'transport_cost', 'utilities_cost', 'other_cost',
            'total_expenses', 'eggs_collected', 'eggs_sold_count',
            'birds_sold_count', 'price_per_bird', 'price_per_egg',
            'sales_revenue', 'profit', 'farmer_observations', 'alerts_generated'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_profit(self, obj):
        return float(obj.sales_revenue - obj.total_expenses)


class FeedPurchaseSerializer(serializers.ModelSerializer):
    """Serializer for feed purchases"""
    feed_type_name = serializers.CharField(source='feed_type.name', read_only=True)
    
    class Meta:
        model = FeedPurchase
        fields = [
            'id', 'purchase_date', 'feed_type', 'feed_type_name',
            'quantity_kg', 'cost_per_kg', 'total_cost', 'invoice_number',
            'supplier_name', 'supplier_contact', 'delivery_date',
            'payment_status', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'total_cost']


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for marketplace orders"""
    customer_name = serializers.CharField(source='user.full_name', read_only=True)
    customer_phone = serializers.CharField(source='user.phone_number', read_only=True)
    items = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'user', 'customer_name', 'customer_phone',
            'status', 'status_display', 'payment_status', 'payment_status_display',
            'payment_method', 'payment_method_display', 'subtotal', 'tax',
            'shipping_cost', 'discount', 'total', 'shipping_address',
            'shipping_city', 'customer_notes', 'items', 'created_at', 'paid_at'
        ]
        read_only_fields = ['id', 'created_at', 'order_number']
    
    def get_items(self, obj):
        items = obj.items.all()
        return OrderItemSerializer(items, many=True).data


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for order items"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price', 'subtotal']


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics"""
    total_farmers = serializers.IntegerField()
    total_flocks = serializers.IntegerField()
    active_flocks = serializers.IntegerField()
    total_birds = serializers.IntegerField()
    total_revenue = serializers.FloatField()
    total_expenses = serializers.FloatField()
    net_profit = serializers.FloatField()
    total_mortality = serializers.IntegerField()


class OrganizationSummarySerializer(serializers.Serializer):
    """Serializer for organization summary"""
    organization_name = serializers.CharField()
    organization_type = serializers.CharField()
    total_farmers = serializers.IntegerField()
    total_flocks = serializers.IntegerField()
    total_revenue = serializers.FloatField()
    total_expenses = serializers.FloatField()
    registered_date = serializers.DateField()