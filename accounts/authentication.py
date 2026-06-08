from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils import timezone
from .models import User

class PINAuthentication(BaseAuthentication):
    def authenticate(self, request):
        # Get credentials from request
        phone_number = request.data.get('phone_number') or request.query_params.get('phone_number')
        pin = request.data.get('pin') or request.query_params.get('pin')
        
        if not phone_number or not pin:
            return None
        
        try:
            user = User.objects.get(phone_number=phone_number)
            
            # Check if user is locked
            if user.locked_until and user.locked_until > timezone.now():
                raise AuthenticationFailed(
                    f'Account locked. Try again after {user.locked_until.strftime("%H:%M:%S")}'
                )
            
            # Verify PIN
            if user.verify_pin(pin) and user.is_active:
                # Update last login
                user.last_login = timezone.now()
                if hasattr(request, 'META'):
                    user.last_login_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
                    user.last_login_user_agent = request.META.get('HTTP_USER_AGENT', '')
                user.save(update_fields=['last_login', 'last_login_ip', 'last_login_user_agent'])
                
                return (user, None)
            else:
                raise AuthenticationFailed('Invalid phone number or PIN')
                
        except User.DoesNotExist:
            raise AuthenticationFailed('Invalid phone number or PIN')
        
        return None
    
    def authenticate_header(self, request):
        return 'PIN realm="api"'