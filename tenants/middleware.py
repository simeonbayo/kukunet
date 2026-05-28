from django.utils.deprecation import MiddlewareMixin

class TenantMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Extract tenant from subdomain or header
        host = request.get_host()
        subdomain = host.split('.')[0]
        
        from .models import Tenant
        try:
            request.tenant = Tenant.objects.get(slug=subdomain, is_active=True)
        except Tenant.DoesNotExist:
            request.tenant = None