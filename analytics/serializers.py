# analytics/serializers.py
from rest_framework import serializers

class DashboardStatsSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    active_farmers = serializers.IntegerField()
    total_tenants = serializers.IntegerField()
    active_flocks = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_commission = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_courses = serializers.IntegerField()
    total_enrollments = serializers.IntegerField()

class FarmAnalyticsSerializer(serializers.Serializer):
    total_birds = serializers.IntegerField()
    mortality_rate = serializers.FloatField()
    feed_conversion_ratio = serializers.FloatField()
    egg_production_rate = serializers.FloatField()
    total_expenses = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    profit_margin = serializers.FloatField()

class SalesReportSerializer(serializers.Serializer):
    date = serializers.DateField()
    total_orders = serializers.IntegerField()
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)