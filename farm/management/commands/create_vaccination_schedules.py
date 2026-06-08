# farm/management/commands/create_vaccination_schedules.py
from django.core.management.base import BaseCommand
from farm.models import VaccinationSchedule

class Command(BaseCommand):
    help = 'Create default vaccination schedules for all bird types'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating vaccination schedules...'))
        
        # Layers Schedule
        layers_data = [
            (0, "Marek's Disease", 'MAREKS', 'Injection', '0.2ml'),
            (0, 'Newcastle Disease', 'NEWCASTLE', 'Eye drop', '1 drop'),
            (2, 'Gumboro', 'GUMBORO', 'Drinking water', 'As per label'),
            # ... add all schedules
        ]
        
        for week, name, vtype, method, dosage in layers_data:
            VaccinationSchedule.objects.get_or_create(
                bird_type='LAYERS',
                week_number=week,
                vaccine_type=vtype,
                defaults={
                    'vaccine_name': name,
                    'administration_method': method,
                    'dosage': dosage
                }
            )
        
        self.stdout.write(self.style.SUCCESS('✅ Vaccination schedules created successfully!'))