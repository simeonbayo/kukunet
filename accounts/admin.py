from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, UserProfile

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('phone_number', 'full_name', 'role', 'tenant', 'is_active', 'is_staff', 'created_at')
    list_filter = ('role', 'is_active', 'is_staff', 'tenant', 'created_at')
    search_fields = ('phone_number', 'full_name')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        (_('Personal info'), {'fields': ('full_name', 'role', 'tenant')}),
        (_('Security'), {'fields': ('pin_hash', 'login_attempts', 'locked_until')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'last_login_ip', 'created_at', 'updated_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'full_name', 'pin_hash', 'role', 'tenant'),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'pin_hash')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'district', 'language', 'created_at')
    list_filter = ('language', 'district')
    search_fields = ('user__phone_number', 'user__full_name', 'district')