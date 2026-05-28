from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import User, UserProfile
from .serializers import UserRegistrationSerializer, LoginSerializer

class RegisterView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Auto-create tenant if needed
        from tenants.models import Tenant
        tenant = Tenant.objects.create(
            name=f"{user.full_name}'s Farm",
            slug=f"farm_{user.id}",
            tenant_code=f"TN{user.id:05d}"
        )
        user.tenant = tenant
        user.save()
        
        return Response({
            'message': 'Registration successful',
            'user_id': user.id,
            'tenant_id': tenant.id
        }, status=status.HTTP_201_CREATED)

class LoginView(APIView):
    authentication_classes = []
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        phone_number = serializer.validated_data['phone_number']
        pin = serializer.validated_data['pin']
        
        from .authentication import PINAuthentication
        auth = PINAuthentication()
        user, _ = auth.authenticate(request)
        
        if user:
            return Response({
                'user_id': user.id,
                'full_name': user.full_name,
                'role': user.role,
                'tenant_id': user.tenant.id if user.tenant else None
            })
        
        return Response({'error': 'Invalid credentials'}, status=400)