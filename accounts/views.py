# accounts/views.py
import logging
from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import AnonRateThrottle
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

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AnonRateThrottle]
    
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
            
            # Create tenant for farmer users
            if user.role == 'FARMER':
                from tenants.models import Tenant
                tenant, created = Tenant.objects.get_or_create(
                    name=f"{user.full_name}'s Farm",
                    defaults={
                        'slug': f"farm_{user.id}",
                        'is_active': True,
                        'subscription_plan': 'BASIC'
                    }
                )
                
                if created:
                    user.tenant = tenant
                    user.save()
            
            return Response({
                'success': True,
                'message': 'Registration successful',
                'data': {
                    'user_id': user.id,
                    'phone_number': user.phone_number,
                    'full_name': user.full_name,
                    'role': user.role,
                    'specialization': getattr(user, 'specialization', None),
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
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
                # THIS IS THE KEY FIX - Create Django session
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