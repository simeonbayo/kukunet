# adminpanel/serializers.py
from rest_framework import serializers
from .models import PlatformSetting, SupportTicket, AuditLog

class PlatformSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformSetting
        fields = '__all__'

class SupportTicketSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = SupportTicket
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'user']

class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = AuditLog
        fields = '__all__'
        read_only_fields = ['id', 'timestamp']