from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    path('api/v1/auth/', include('accounts.urls')),
    path('api/v1/', include('farm.urls')),
    path('api/v1/', include('marketplace.urls')),
    path('api/v1/', include('courses.urls')),
    path('api/v1/admin/', include('adminpanel.urls')),
    path('api/v1/analytics/', include('analytics.urls')),
    
    # Frontend views (to be implemented)
    #path('', include('frontend.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)