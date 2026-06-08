# accounts/serializers.py
from rest_framework import serializers
from .models import User, UserProfile

class UserRegistrationSerializer(serializers.ModelSerializer):
    pin = serializers.CharField(write_only=True, min_length=4, max_length=4)
    confirm_pin = serializers.CharField(write_only=True, min_length=4, max_length=4)
    
    # Field officer fields
    specialization = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    license_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    years_experience = serializers.IntegerField(required=False, default=0)
    assigned_districts = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    # Organization fields
    organization_type = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    registration_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    tax_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    website = serializers.URLField(required=False, allow_blank=True, allow_null=True)
    
    class Meta:
        model = User
        fields = [
            'phone_number', 'full_name', 'pin', 'confirm_pin', 'role',
            'specialization', 'license_number', 'years_experience', 'assigned_districts',
            'organization_type', 'registration_number', 'tax_id', 'website'
        ]
    
    def validate_phone_number(self, value):
        # Clean phone number
        value = ''.join(filter(str.isdigit, value))
        if len(value) < 10:
            raise serializers.ValidationError("Phone number must be at least 10 digits")
        if len(value) > 15:
            raise serializers.ValidationError("Phone number too long")
        return value
    
    def validate_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("PIN must contain only numbers")
        if len(value) != 4:
            raise serializers.ValidationError("PIN must be exactly 4 digits")
        return value
    
    def validate(self, data):
        if data['pin'] != data['confirm_pin']:
            raise serializers.ValidationError({"confirm_pin": "PINs do not match"})
        
        # Validate role
        valid_roles = ['FARMER', 'CUSTOMER', 'SUPPLIER', 'TRAINER', 'FIELD_OFFICER', 'ORGANIZATION', 'ADMIN']
        if data.get('role') not in valid_roles:
            raise serializers.ValidationError({"role": f"Invalid role. Choose from: {', '.join(valid_roles)}"})
        
        return data
    
    def create(self, validated_data):
        pin = validated_data.pop('pin')
        validated_data.pop('confirm_pin')
        
        # Extract field officer fields
        specialization = validated_data.pop('specialization', None)
        license_number = validated_data.pop('license_number', None)
        years_experience = validated_data.pop('years_experience', 0)
        assigned_districts = validated_data.pop('assigned_districts', None)
        
        # Extract organization fields
        organization_type = validated_data.pop('organization_type', None)
        registration_number = validated_data.pop('registration_number', None)
        tax_id = validated_data.pop('tax_id', None)
        website = validated_data.pop('website', None)
        
        # Create user
        user = User.objects.create_user(pin=pin, **validated_data)
        
        # Set field officer specific fields
        if user.role == 'FIELD_OFFICER':
            user.specialization = specialization or ''
            user.license_number = license_number or ''
            user.years_experience = years_experience or 0
            user.assigned_districts = assigned_districts or ''
            user.save()
        
        # Set organization specific fields
        if user.role == 'ORGANIZATION':
            user.organization_name = user.full_name
            user.organization_type = organization_type or ''
            user.registration_number = registration_number or ''
            user.tax_id = tax_id or ''
            user.website = website or ''
            user.save()
        
        # Create user profile
        UserProfile.objects.get_or_create(user=user)
        
        return user

class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    pin = serializers.CharField(min_length=4, max_length=4)

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'user']

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'phone_number', 'full_name', 'role', 'tenant', 
            'is_active', 'last_login', 'created_at', 'profile',
            'specialization', 'license_number', 'years_experience', 'assigned_districts',
            'organization_name', 'organization_type', 'registration_number', 'tax_id', 'website'
        ]
        read_only_fields = ['id', 'last_login', 'created_at']