# farm/serializers.py
from rest_framework import serializers
from .models import Farm, House, FlockBatch, DailyRecord, VaccinationRecord, Expense

class FarmSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farm
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'tenant']

class HouseSerializer(serializers.ModelSerializer):
    farm_name = serializers.CharField(source='farm.farm_name', read_only=True)
    
    class Meta:
        model = House
        fields = '__all__'
        read_only_fields = ['id', 'tenant']

class FlockBatchSerializer(serializers.ModelSerializer):
    farm_name = serializers.CharField(source='farm.farm_name', read_only=True)
    house_name = serializers.CharField(source='house.name', read_only=True)
    age_days = serializers.IntegerField(read_only=True)
    mortality_rate = serializers.FloatField(read_only=True)
    
    class Meta:
        model = FlockBatch
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'tenant']

class DailyRecordSerializer(serializers.ModelSerializer):
    batch_name = serializers.CharField(source='batch.batch_name', read_only=True)
    
    class Meta:
        model = DailyRecord
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'tenant']

class VaccinationSerializer(serializers.ModelSerializer):
    batch_name = serializers.CharField(source='batch.batch_name', read_only=True)
    
    class Meta:
        model = VaccinationRecord
        fields = '__all__'
        read_only_fields = ['id', 'tenant']

class ExpenseSerializer(serializers.ModelSerializer):
    farm_name = serializers.CharField(source='farm.farm_name', read_only=True)
    batch_name = serializers.CharField(source='batch.batch_name', read_only=True, allow_null=True)
    
    class Meta:
        model = Expense
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'tenant']