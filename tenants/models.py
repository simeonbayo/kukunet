from django.db import models
from django.utils.text import slugify
import uuid

class Tenant(models.Model):
    PLAN_CHOICES = [
        ('BASIC', 'Basic'),
        ('PRO', 'Professional'),
        ('ENTERPRISE', 'Enterprise'),
    ]
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('SUSPENDED', 'Suspended'),
        ('EXPIRED', 'Expired'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    tenant_code = models.CharField(max_length=10, unique=True, blank=True)
    subscription_plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='BASIC')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    max_users = models.IntegerField(default=10)
    max_farms = models.IntegerField(default=5)
    subscription_start = models.DateField(null=True, blank=True)
    subscription_end = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.tenant_code:
            self.tenant_code = f"TN{str(uuid.uuid4())[:8].upper()}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    
    class Meta:
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['tenant_code']),
            models.Index(fields=['status']),
        ]

class TenantSettings(models.Model):
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name='settings')
    currency = models.CharField(max_length=3, default='UGX')
    currency_symbol = models.CharField(max_length=5, default='UGX')
    timezone = models.CharField(max_length=50, default='Africa/Kampala')
    default_language = models.CharField(max_length=10, default='en')
    date_format = models.CharField(max_length=20, default='Y-m-d')
    logo = models.ImageField(upload_to='tenant_logos/', null=True, blank=True)
    primary_color = models.CharField(max_length=7, default='#2E7D32')
    secondary_color = models.CharField(max_length=7, default='#FF8F00')
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Settings for {self.tenant.name}"