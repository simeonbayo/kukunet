from django.core.management.base import BaseCommand
from accounts.models import User
from tenants.models import Tenant

class Command(BaseCommand):
    help = 'Seed initial data for development'
    
    def handle(self, *args, **options):
        self.stdout.write("Seeding data...")
        
        # Create superuser
        if not User.objects.filter(phone_number='256700000000').exists():
            User.objects.create_superuser(
                phone_number='256700000000',
                pin='1234',
                full_name='Super Admin'
            )
            self.stdout.write(self.style.SUCCESS("Superuser created"))
        
        # Create sample tenant
        tenant, created = Tenant.objects.get_or_create(
            name='Demo Farm',
            defaults={
                'slug': 'demo-farm',
                'subscription_plan': 'PRO'
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS("Demo tenant created"))
        
        # Create sample farmer
        if not User.objects.filter(phone_number='256701234567').exists():
            farmer = User.objects.create_user(
                phone_number='256701234567',
                pin='1234',
                full_name='Demo Farmer',
                role='FARMER',
                tenant=tenant
            )
            self.stdout.write(self.style.SUCCESS("Demo farmer created"))
        
        self.stdout.write(self.style.SUCCESS("Data seeding complete!"))