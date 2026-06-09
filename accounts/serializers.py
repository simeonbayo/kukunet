# accounts/serializers.py
from rest_framework import serializers
from .models import User, UserProfile

class UserRegistrationSerializer(serializers.ModelSerializer):
    pin = serializers.CharField(write_only=True, required=True, min_length=4, max_length=6)
    confirm_pin = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = [
            'phone_number', 'full_name', 'pin', 'confirm_pin',
            'role', 'organization_type', 'organization_name',
            'registration_number', 'tax_id', 'website',
            'specialization', 'license_number', 'years_experience', 'assigned_districts'
        ]
    
    def validate_phone_number(self, value):
        """Validate phone number format"""
        from .models import User
        # Normalize phone number
        phone_number = ''.join(filter(str.isdigit, value))
        
        if len(phone_number) == 9:
            phone_number = '256' + phone_number
        elif len(phone_number) == 10 and phone_number.startswith('0'):
            phone_number = '256' + phone_number[1:]
        
        if User.objects.filter(phone_number=phone_number).exists():
            raise serializers.ValidationError("User with this phone number already exists")
        
        return phone_number
    
    def validate(self, data):
        """Validate pin and confirm_pin match"""
        if data.get('pin') != data.get('confirm_pin'):
            raise serializers.ValidationError({"confirm_pin": "PIN numbers do not match"})
        
        # Validate organization fields if role is ORGANIZATION
        if data.get('role') == 'ORGANIZATION':
            if not data.get('organization_type'):
                raise serializers.ValidationError({"organization_type": "Organization type is required for organization accounts"})
        
        # Validate field officer fields if role is FIELD_OFFICER
        if data.get('role') == 'FIELD_OFFICER':
            if not data.get('specialization'):
                raise serializers.ValidationError({"specialization": "Specialization is required for field officers"})
        
        return data
    
    def create(self, validated_data):
        # Remove confirm_pin as it's not needed for user creation
        validated_data.pop('confirm_pin')
        pin = validated_data.pop('pin')
        
        # Create user
        user = User.objects.create_user(
            phone_number=validated_data.get('phone_number'),
            pin=pin,
            full_name=validated_data.get('full_name', ''),
            role=validated_data.get('role', 'FARMER'),
            organization_type=validated_data.get('organization_type', ''),
            organization_name=validated_data.get('organization_name', ''),
            registration_number=validated_data.get('registration_number', ''),
            tax_id=validated_data.get('tax_id', ''),
            website=validated_data.get('website', ''),
            specialization=validated_data.get('specialization', ''),
            license_number=validated_data.get('license_number', ''),
            years_experience=validated_data.get('years_experience', 0),
            assigned_districts=validated_data.get('assigned_districts', '')
        )
        
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