# accounts/serializers.py
from rest_framework import serializers
from .models import User, UserProfile

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'phone_number', 'full_name', 'role', 'tenant', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']

class UserRegistrationSerializer(serializers.ModelSerializer):
    pin = serializers.CharField(write_only=True, min_length=4, max_length=4)
    
    class Meta:
        model = User
        fields = ['phone_number', 'full_name', 'pin', 'role']
    
    def create(self, validated_data):
        pin = validated_data.pop('pin')
        user = User.objects.create_user(
            phone_number=validated_data['phone_number'],
            pin=pin,
            full_name=validated_data.get('full_name', ''),
            role=validated_data.get('role', 'FARMER')
        )
        return user

class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    pin = serializers.CharField(min_length=4, max_length=4)

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = '__all__'
        read_only_fields = ['id', 'user']