from django.contrib import admin
from .models import Tenant, TenantSettings

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'tenant_code', 'subscription_plan', 'status', 'is_active', 'created_at')
    list_filter = ('subscription_plan', 'status', 'is_active')
    search_fields = ('name', 'slug', 'tenant_code')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('tenant_code', 'created_at', 'updated_at')

@admin.register(TenantSettings)
class TenantSettingsAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'currency', 'timezone', 'default_language')
    list_filter = ('currency', 'timezone', 'default_language')
    search_fields = ('tenant__name',)