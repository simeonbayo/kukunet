# farm/serializers.py
from rest_framework import serializers
from django.db.models import Sum
from .models import Farm, House, FlockBatch, DailyRecord, VaccinationRecord


class FarmSerializer(serializers.ModelSerializer):
    total_birds = serializers.SerializerMethodField()
    active_flocks = serializers.SerializerMethodField()
    
    class Meta:
        model = Farm
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'tenant', 'created_by']
    
    def get_total_birds(self, obj):
        """Calculate total birds across all active flocks"""
        try:
            # Sum current_quantity of all active flocks in this farm
            total = obj.flock_batches.filter(status='ACTIVE').aggregate(
                total=Sum('current_quantity')
            )['total']
            print(f"Farm {obj.farm_name} total birds: {total}")  # Debug print
            return total or 0
        except Exception as e:
            print(f"Error calculating total birds for farm {obj.farm_name}: {e}")
            return 0
    
    def get_active_flocks(self, obj):
        """Count active flocks"""
        try:
            count = obj.flock_batches.filter(status='ACTIVE').count()
            return count
        except:
            return 0


class HouseSerializer(serializers.ModelSerializer):
    farm_name = serializers.CharField(source='farm.farm_name', read_only=True)
    current_population = serializers.IntegerField(read_only=True)
    occupancy_rate = serializers.FloatField(read_only=True)
    
    class Meta:
        model = House
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'tenant']


class FlockBatchSerializer(serializers.ModelSerializer):
    farm_name = serializers.CharField(source='farm.farm_name', read_only=True)
    house_name = serializers.CharField(source='house.name', read_only=True, allow_null=True)
    age_days = serializers.IntegerField(read_only=True)
    age_weeks = serializers.IntegerField(read_only=True)
    mortality_rate = serializers.FloatField(read_only=True)
    survival_rate = serializers.FloatField(read_only=True)
    total_feed_consumed = serializers.FloatField(read_only=True)
    total_eggs_produced = serializers.IntegerField(read_only=True)
    avg_daily_eggs = serializers.FloatField(read_only=True)
    feed_conversion_ratio = serializers.FloatField(read_only=True)
    
    class Meta:
        model = FlockBatch
        fields = '__all__'
        read_only_fields = ['id', 'batch_number', 'created_at', 'updated_at', 'tenant', 'created_by']


class DailyRecordSerializer(serializers.ModelSerializer):
    batch_name = serializers.CharField(source='batch.batch_name', read_only=True)
    mortality_rate = serializers.FloatField(read_only=True)
    egg_production_percent = serializers.FloatField(read_only=True)
    alerts = serializers.JSONField(source='alerts_generated', read_only=True)
    feed_conversion_ratio_calculated = serializers.FloatField(read_only=True)
    
    class Meta:
        model = DailyRecord
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'tenant', 'recorded_by',
                           'closing_bird_count', 'feed_consumed_kg', 'eggs_saleable',
                           'egg_production_percent', 'sales_revenue', 'total_expenses',
                           'feed_conversion_ratio', 'weight_gain_kg']


class DailyRecordCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for daily data entry with feed management integration"""
    
    class Meta:
        model = DailyRecord
        fields = [
            'batch', 'date', 'opening_bird_count', 'mortality', 'birds_sold',
            'feed_given_kg', 'feed_remaining_kg', 'feed_type', 'feed_cost',
            'water_provided_liters', 'water_consumed_liters', 'eggs_collected', 'eggs_broken',
            'avg_weight_kg', 'drug_name', 'dosage', 'temperature_c',
            'humidity_percent', 'litter_condition', 'farmer_observations'
        ]


class VaccinationRecordSerializer(serializers.ModelSerializer):
    batch_name = serializers.CharField(source='batch.batch_name', read_only=True)
    
    class Meta:
        model = VaccinationRecord
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'tenant', 'created_by']