from django.db import models

class Tenant(models.Model):
    PLAN_CHOICES = [
        ('BASIC', 'Basic'),
        ('PRO', 'Professional'),
        ('ENTERPRISE', 'Enterprise'),
    ]
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    tenant_code = models.CharField(max_length=10, unique=True)
    subscription_plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='BASIC')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class TenantSettings(models.Model):
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name='settings')
    currency = models.CharField(max_length=3, default='UGX')
    timezone = models.CharField(max_length=50, default='Africa/Kampala')
    default_language = models.CharField(max_length=10, default='en')