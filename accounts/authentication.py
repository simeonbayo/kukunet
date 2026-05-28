from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import User

class PINAuthentication(BaseAuthentication):
    def authenticate(self, request):
        phone_number = request.data.get('phone_number')
        pin = request.data.get('pin')
        
        if not phone_number or not pin:
            return None
        
        try:
            user = User.objects.get(phone_number=phone_number)
            if user.verify_pin(pin) and user.is_active:
                return (user, None)
        except User.DoesNotExist:
            raise AuthenticationFailed('Invalid credentials')
        
        raise AuthenticationFailed('Invalid credentials')