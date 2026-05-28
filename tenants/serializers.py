# tenants/serializers.py
from rest_framework import serializers
from .models import Tenant, TenantSettings

class TenantSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantSettings
        fields = '__all__'
        read_only_fields = ['id', 'tenant']

class TenantSerializer(serializers.ModelSerializer):
    settings = TenantSettingsSerializer(read_only=True)
    
    class Meta:
        model = Tenant
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'tenant_code']