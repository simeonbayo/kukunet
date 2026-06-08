# organizations/serializers.py
from rest_framework import serializers
from .models import OrganizationFarmer, OrganizationProject, OrganizationMember, Partnership

class OrganizationFarmerSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationFarmer
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'organization', 'created_by']

class OrganizationProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationProject
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'organization']

class OrganizationMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationMember
        fields = '__all__'
        read_only_fields = ['id', 'joined_date', 'organization']

class PartnershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partnership
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'organization']