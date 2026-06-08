from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import get_object_or_404
from .models import Tenant

class TenantMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Skip for admin and API docs
        if request.path.startswith('/admin') or request.path.startswith('/api/docs'):
            request.tenant = None
            return
        
        # Extract tenant from subdomain or header
        host = request.get_host().split(':')[0]
        subdomain = host.split('.')[0] if '.' in host else None
        
        # Check for tenant in header (for API calls)
        tenant_code = request.headers.get('X-Tenant-Code')
        
        if tenant_code:
            try:
                request.tenant = get_object_or_404(Tenant, tenant_code=tenant_code, is_active=True)
                return
            except:
                pass
        
        if subdomain and subdomain != 'www' and subdomain != 'localhost':
            try:
                request.tenant = get_object_or_404(Tenant, slug=subdomain, is_active=True)
                return
            except:
                pass
        
        # For development, try to get from user
        if hasattr(request, 'user') and request.user.is_authenticated:
            request.tenant = request.user.tenant
        else:
            request.tenant = None