# accounts/views.py
import logging
from rest_framework import generics, status, views
from django.utils.text import slugify
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import AnonRateThrottle
from django.db import transaction
from django.contrib.auth import logout as django_logout, login as django_login
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from .models import User, UserProfile
from .serializers import (
    UserRegistrationSerializer, 
    LoginSerializer, 
    UserSerializer, 
    UserProfileSerializer
)
from tenants.models import Tenant  # <-- ADD THIS IMPORT AT THE TOP

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AnonRateThrottle]
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        logger.info(f"Registration attempt from {request.META.get('REMOTE_ADDR', 'unknown')}")
        logger.info(f"Request data: {request.data}")
        
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            logger.error(f"Registration validation errors: {serializer.errors}")
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = serializer.save()
            logger.info(f"User registered successfully: {user.phone_number} (Role: {user.role})")
            
            # Handle tenant assignment based on role and join code
            organization_join_code = request.data.get('organization_join_code', '')
            
            # If farmer and has organization join code, join existing organization
            if user.role == 'FARMER' and organization_join_code:
                try:
                    # Find the organization tenant by code
                    org_tenant = Tenant.objects.get(tenant_code=organization_join_code, is_active=True)
                    user.tenant = org_tenant
                    user.save(update_fields=['tenant'])
                    logger.info(f"Farmer {user.phone_number} joined organization: {org_tenant.name}")
                    
                    return Response({
                        'success': True,
                        'message': f'Registration successful! You have joined {org_tenant.name}.',
                        'data': {
                            'user_id': user.id,
                            'phone_number': user.phone_number,
                            'full_name': user.full_name,
                            'role': user.role,
                            'tenant_id': user.tenant.id if user.tenant else None,
                            'tenant_name': user.tenant.name if user.tenant else None,
                            'joined_organization': True,
                            'organization_name': org_tenant.name
                        }
                    }, status=status.HTTP_201_CREATED)
                except Tenant.DoesNotExist:
                    logger.warning(f"Invalid organization code: {organization_join_code}")
                    # Fall through to create individual tenant
            
            # Create tenant for FARMER role (individual farmer)
            if user.role == 'FARMER' and not user.tenant:
                tenant_name = f"{user.full_name}'s Farm" if user.full_name else f"Farmer_{user.phone_number}"
                
                # Generate unique slug
                base_slug = slugify(tenant_name)
                slug = base_slug
                counter = 1
                while Tenant.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                
                tenant, created = Tenant.objects.get_or_create(
                    name=tenant_name,
                    defaults={
                        'slug': slug,
                        'tenant_code': f"FARM{user.id}{str(user.id).zfill(4)}",
                        'subscription_plan': 'BASIC',
                        'status': 'ACTIVE',
                        'max_users': 5,
                        'max_farms': 3,
                        'is_active': True
                    }
                )
                
                if created:
                    user.tenant = tenant
                    user.save(update_fields=['tenant'])
                    logger.info(f"Created farmer tenant: {tenant_name} for user {user.phone_number}")
            
            # Create tenant for ORGANIZATION role
            elif user.role == 'ORGANIZATION' and not user.tenant:
                # Use organization name or create from type
                if user.organization_name:
                    tenant_name = user.organization_name
                else:
                    org_type_display = dict(User.ORGANIZATION_TYPES).get(user.organization_type, 'Organization')
                    tenant_name = f"{org_type_display}_{user.phone_number}"
                
                # Generate unique slug
                base_slug = slugify(tenant_name)
                slug = base_slug
                counter = 1
                while Tenant.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                
                # Determine plan based on organization type
                if user.organization_type == 'AGRIBUSINESS':
                    subscription_plan = 'PRO'
                    max_users = 100
                    max_farms = 50
                elif user.organization_type == 'COOPERATIVE':
                    subscription_plan = 'PRO'
                    max_users = 200
                    max_farms = 100
                elif user.organization_type == 'NGO':
                    subscription_plan = 'NON_PROFIT'
                    max_users = 50
                    max_farms = 20
                elif user.organization_type == 'GOVERNMENT':
                    subscription_plan = 'ENTERPRISE'
                    max_users = 500
                    max_farms = 200
                elif user.organization_type == 'RESEARCH':
                    subscription_plan = 'RESEARCH'
                    max_users = 100
                    max_farms = 30
                else:
                    subscription_plan = 'BASIC'
                    max_users = 20
                    max_farms = 10
                
                tenant, created = Tenant.objects.get_or_create(
                    name=tenant_name,
                    defaults={
                        'slug': slug,
                        'tenant_code': f"ORG{user.id}{str(user.id).zfill(4)}",
                        'subscription_plan': subscription_plan,
                        'status': 'ACTIVE',
                        'max_users': max_users,
                        'max_farms': max_farms,
                        'is_active': True
                    }
                )
                
                if created:
                    user.tenant = tenant
                    user.save(update_fields=['tenant'])
                    logger.info(f"Created organization tenant: {tenant_name} for {user.organization_type}")
            
            # For other roles, assign to default tenant
            elif not user.tenant:
                default_tenant, created = Tenant.objects.get_or_create(
                    name="Default Tenant",
                    defaults={
                        'slug': 'default',
                        'tenant_code': 'DEFAULT',
                        'subscription_plan': 'BASIC',
                        'status': 'ACTIVE',
                        'is_active': True
                    }
                )
                user.tenant = default_tenant
                user.save(update_fields=['tenant'])
                logger.info(f"Assigned default tenant to {user.role} user: {user.phone_number}")
            
            # Prepare response message
            message = 'Registration successful'
            if user.role == 'FARMER' and organization_join_code:
                message = f'Registration successful! You have joined {user.tenant.name}.'
            elif user.role == 'FARMER':
                message = 'Registration successful! Your farm has been created.'
            elif user.role == 'ORGANIZATION':
                message = f'Registration successful! Your organization "{user.tenant.name}" has been created.'
            
            return Response({
                'success': True,
                'message': message,
                'data': {
                    'user_id': user.id,
                    'phone_number': user.phone_number,
                    'full_name': user.full_name,
                    'role': user.role,
                    'organization_type': getattr(user, 'organization_type', None),
                    'organization_name': getattr(user, 'organization_name', None),
                    'tenant_id': user.tenant.id if user.tenant else None,
                    'tenant_name': user.tenant.name if user.tenant else None,
                    'tenant_code': user.tenant.tenant_code if user.tenant else None,
                    'specialization': getattr(user, 'specialization', None),
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Registration error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'Registration failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(views.APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AnonRateThrottle]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Invalid input'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        phone_number = serializer.validated_data['phone_number']
        pin = serializer.validated_data['pin']
        
        try:
            user = User.objects.get(phone_number=phone_number)
            
            if not user.is_active:
                return Response({
                    'success': False,
                    'message': 'Account is deactivated'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            if user.verify_pin(pin):
                # Create Django session
                django_login(request, user)
                
                return Response({
                    'success': True,
                    'message': 'Login successful',
                    'data': {
                        'user_id': user.id,
                        'phone_number': user.phone_number,
                        'full_name': user.full_name,
                        'role': user.role,
                    }
                })
            else:
                return Response({
                    'success': False,
                    'message': 'Invalid phone number or PIN'
                }, status=status.HTTP_401_UNAUTHORIZED)
                
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Invalid phone number or PIN'
            }, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(views.APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        django_logout(request)
        return Response({
            'success': True,
            'message': 'Logout successful'
        })


class ChangePinView(views.APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        old_pin = request.data.get('old_pin')
        new_pin = request.data.get('new_pin')
        confirm_pin = request.data.get('confirm_pin')
        
        if not all([old_pin, new_pin, confirm_pin]):
            return Response({
                'success': False,
                'message': 'All fields are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if len(new_pin) != 4 or not new_pin.isdigit():
            return Response({
                'success': False,
                'message': 'PIN must be 4 digits'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if new_pin != confirm_pin:
            return Response({
                'success': False,
                'message': 'New PINs do not match'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not request.user.verify_pin(old_pin):
            return Response({
                'success': False,
                'message': 'Old PIN is incorrect'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        request.user.set_pin(new_pin)
        request.user.save()
        
        return Response({
            'success': True,
            'message': 'PIN changed successfully'
        })


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user