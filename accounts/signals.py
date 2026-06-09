# accounts/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from tenants.models import Tenant
from django.utils.text import slugify

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_tenant(sender, instance, created, **kwargs):
    """Automatically create tenant for organization users"""
    if created and instance.role == 'ORGANIZATION':
        # Only create tenant if not already assigned
        if not instance.tenant:
            # Create tenant for organization users
            tenant_name = instance.organization_name or f"{instance.get_organization_type_display()}_{instance.phone_number}"
            
            # Determine plan based on organization type
            if instance.organization_type == 'AGRIBUSINESS':
                subscription_plan = 'PRO'
                max_users = 100
                max_farms = 50
            elif instance.organization_type == 'COOPERATIVE':
                subscription_plan = 'PRO'
                max_users = 200
                max_farms = 100
            else:
                subscription_plan = 'BASIC'
                max_users = 20
                max_farms = 10
            
            tenant, created = Tenant.objects.get_or_create(
                name=tenant_name,
                defaults={
                    'slug': slugify(tenant_name)[:50],
                    'tenant_code': f"ORG{instance.id}{str(instance.id).zfill(4)}",
                    'subscription_plan': subscription_plan,
                    'status': 'ACTIVE',
                    'max_users': max_users,
                    'max_farms': max_farms,
                    'is_active': True
                }
            )
            
            instance.tenant = tenant
            instance.save(update_fields=['tenant'])
            
            print(f"✅ Auto-created tenant '{tenant.name}' for {instance.get_organization_type_display()} user: {instance.phone_number}")
    
    elif created and instance.role == 'FARMER':
        if not instance.tenant:
            tenant_name = f"{instance.full_name}'s Farm" if instance.full_name else f"Farmer_{instance.phone_number}"
            
            tenant, created = Tenant.objects.get_or_create(
                name=tenant_name,
                defaults={
                    'slug': slugify(tenant_name)[:50],
                    'tenant_code': f"FARM{instance.id}{str(instance.id).zfill(4)}",
                    'subscription_plan': 'BASIC',
                    'status': 'ACTIVE',
                    'max_users': 5,
                    'max_farms': 3,
                    'is_active': True
                }
            )
            
            instance.tenant = tenant
            instance.save(update_fields=['tenant'])
            
            print(f"✅ Auto-created tenant '{tenant.name}' for farmer: {instance.phone_number}")