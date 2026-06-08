"""
Management command to create feeding guide templates for different bird types.
Usage: python manage.py create_feeding_guides
       python manage.py create_feeding_guides --clear
       python manage.py create_feeding_guides --bird-type BROILERS
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import transaction
from farm.models import FeedType, FeedCategory, FeedingGuide


class Command(BaseCommand):
    help = 'Create feeding guide templates for Broilers, Layers, and Kuroilers'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing feeding guides before creating new ones',
        )
        parser.add_argument(
            '--bird-type',
            type=str,
            choices=['BROILERS', 'LAYERS', 'KUROILERS', 'ALL'],
            default='ALL',
            help='Specific bird type to create guides for (default: ALL)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating',
        )
    
    def handle(self, *args, **options):
        clear_existing = options['clear']
        bird_type = options['bird_type']
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('FEEDING GUIDE CREATION TOOL'))
        self.stdout.write(self.style.SUCCESS('='*60))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY RUN MODE - No changes will be made\n'))
        
        # Clear existing guides if requested
        if clear_existing:
            self.clear_existing_guides(bird_type, dry_run)
        
        # Create or update feed categories and types
        self.create_feed_categories(dry_run)
        feed_types = self.create_feed_types(dry_run)
        
        # Create feeding guides
        if bird_type == 'ALL' or bird_type == 'BROILERS':
            self.create_broiler_guides(feed_types, dry_run)
        
        if bird_type == 'ALL' or bird_type == 'LAYERS':
            self.create_layer_guides(feed_types, dry_run)
        
        if bird_type == 'ALL' or bird_type == 'KUROILERS':
            self.create_kuroiler_guides(feed_types, dry_run)
        
        # Summary
        self.print_summary(bird_type, dry_run)
    
    def clear_existing_guides(self, bird_type, dry_run):
        """Clear existing feeding guides"""
        if bird_type == 'ALL':
            guides = FeedingGuide.objects.all()
            count = guides.count()
            if not dry_run:
                guides.delete()
            self.stdout.write(self.style.WARNING(f'🗑️  Cleared {count} existing feeding guides'))
        else:
            guides = FeedingGuide.objects.filter(bird_type=bird_type)
            count = guides.count()
            if not dry_run:
                guides.delete()
            self.stdout.write(self.style.WARNING(f'🗑️  Cleared {count} existing {bird_type} feeding guides'))
    
    def create_feed_categories(self, dry_run):
        """Create feed categories"""
        categories = [
            {'name': 'Poultry Feed', 'description': 'Complete poultry feed formulations', 'icon': 'fa-seedling'},
            {'name': 'Starter Feed', 'description': 'Feed for young chicks (0-4 weeks)', 'icon': 'fa-baby-carriage'},
            {'name': 'Grower Feed', 'description': 'Feed for growing birds (4-16 weeks)', 'icon': 'fa-chart-line'},
            {'name': 'Finisher Feed', 'description': 'Feed for finishing birds (16+ weeks)', 'icon': 'fa-flag-checkered'},
            {'name': 'Layer Feed', 'description': 'Feed for laying hens', 'icon': 'fa-egg'},
        ]
        
        created_categories = []
        for cat_data in categories:
            if dry_run:
                self.stdout.write(f'  Would create category: {cat_data["name"]}')
                created_categories.append(cat_data['name'])
            else:
                category, created = FeedCategory.objects.get_or_create(
                    name=cat_data['name'],
                    defaults={
                        'description': cat_data['description'],
                        'icon': cat_data['icon']
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'  ✅ Created category: {category.name}'))
                else:
                    self.stdout.write(f'  ⚠️ Category already exists: {category.name}')
                created_categories.append(category.name)
        
        return created_categories
    
    def create_feed_types(self, dry_run):
        """Create feed types"""
        feed_types_data = [
            # Broiler feeds
            {'name': 'Broiler Starter', 'feed_stage': 'BROILER_STARTER', 'category': 'Starter Feed', 
             'description': 'Complete feed for broiler chicks (0-3 weeks)', 'protein': 22.0, 'energy': 3.2},
            {'name': 'Broiler Finisher', 'feed_stage': 'BROILER_FINISHER', 'category': 'Finisher Feed',
             'description': 'Complete feed for broiler growers (3-6 weeks)', 'protein': 20.0, 'energy': 3.1},
            
            # Layer feeds
            {'name': 'Layer Starter', 'feed_stage': 'STARTER', 'category': 'Starter Feed',
             'description': 'Feed for layer chicks (0-6 weeks)', 'protein': 20.0, 'energy': 2.9},
            {'name': 'Layer Grower', 'feed_stage': 'GROWER', 'category': 'Grower Feed',
             'description': 'Feed for growing layers (6-18 weeks)', 'protein': 18.0, 'energy': 2.7},
            {'name': 'Layer Mash', 'feed_stage': 'LAYER_MASH', 'category': 'Layer Feed',
             'description': 'Complete feed for laying hens (18+ weeks)', 'protein': 16.0, 'energy': 2.6},
            
            # Kuroiler feeds
            {'name': 'Kuroiler Starter', 'feed_stage': 'STARTER', 'category': 'Starter Feed',
             'description': 'Feed for Kuroiler chicks (0-4 weeks)', 'protein': 20.0, 'energy': 2.9},
            {'name': 'Kuroiler Grower', 'feed_stage': 'GROWER', 'category': 'Grower Feed',
             'description': 'Feed for growing Kuroilers (4-16 weeks)', 'protein': 18.0, 'energy': 2.7},
            {'name': 'Kuroiler Finisher', 'feed_stage': 'FINISHER', 'category': 'Finisher Feed',
             'description': 'Feed for finishing Kuroilers (16+ weeks)', 'protein': 16.0, 'energy': 2.6},
        ]
        
        feed_type_objects = {}
        
        for ft_data in feed_types_data:
            # Get or create category
            category = FeedCategory.objects.filter(name=ft_data['category']).first()
            
            if dry_run:
                self.stdout.write(f'  Would create feed type: {ft_data["name"]}')
                feed_type_objects[ft_data['name']] = ft_data['name']
            else:
                feed_type, created = FeedType.objects.get_or_create(
                    name=ft_data['name'],
                    defaults={
                        'feed_stage': ft_data['feed_stage'],
                        'category': category,
                        'description': ft_data['description'],
                        'protein_percentage': ft_data['protein'],
                        'energy_mj_kg': ft_data['energy'],
                        'is_active': True
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'  ✅ Created feed type: {feed_type.name}'))
                else:
                    self.stdout.write(f'  ⚠️ Feed type already exists: {feed_type.name}')
                feed_type_objects[ft_data['name']] = feed_type
        
        return feed_type_objects
    
    def create_broiler_guides(self, feed_types, dry_run):
        """Create feeding guides for Broilers"""
        self.stdout.write(self.style.SUCCESS('\n📋 Creating Broiler feeding guides...'))
        
        broiler_guides = [
            # Week, Daily Feed (g), Expected Weight (kg)
            (1, 45, 0.18),
            (2, 65, 0.45),
            (3, 85, 0.90),
            (4, 105, 1.40),
            (5, 125, 1.90),
            (6, 140, 2.30),
        ]
        
        feed_type_map = {
            1: 'Broiler Starter',
            2: 'Broiler Starter', 
            3: 'Broiler Starter',
            4: 'Broiler Finisher',
            5: 'Broiler Finisher',
            6: 'Broiler Finisher',
        }
        
        for week, daily_feed, expected_weight in broiler_guides:
            feed_type_name = feed_type_map[week]
            feed_type = feed_types.get(feed_type_name) if not dry_run else None
            
            if dry_run:
                self.stdout.write(f'  Would create: Week {week}: {daily_feed}g/day, {expected_weight}kg expected')
                continue
            
            guide, created = FeedingGuide.objects.get_or_create(
                bird_type='BROILERS',
                week_start=week,
                week_end=week,
                defaults={
                    'feed_type': feed_type,
                    'daily_feed_per_bird_grams': daily_feed,
                    'expected_weight_kg': expected_weight,
                    'notes': f'Broiler week {week} - Standard commercial broiler feeding program'
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✅ Created: Week {week}: {daily_feed}g/day'))
            else:
                self.stdout.write(f'  ⚠️ Already exists: Week {week}')
    
    def create_layer_guides(self, feed_types, dry_run):
        """Create feeding guides for Layers"""
        self.stdout.write(self.style.SUCCESS('\n📋 Creating Layer feeding guides...'))
        
        layer_guides = [
            # Week Start, Week End, Daily Feed (g), Expected Weight (kg), Expected Eggs (per 100 birds)
            (1, 4, 15, 0.10, None),
            (5, 8, 25, 0.30, None),
            (9, 12, 40, 0.70, None),
            (13, 16, 55, 1.10, None),
            (17, 20, 65, 1.40, 5),
            (21, 30, 70, 1.60, 85),
            (31, 40, 75, 1.70, 80),
            (41, 50, 75, 1.75, 75),
            (51, 60, 75, 1.80, 70),
            (61, 72, 75, 1.85, 65),
        ]
        
        feed_type_map = {
            (1, 4): 'Layer Starter',
            (5, 8): 'Layer Starter',
            (9, 12): 'Layer Grower',
            (13, 16): 'Layer Grower',
            (17, 20): 'Layer Mash',
            (21, 30): 'Layer Mash',
            (31, 40): 'Layer Mash',
            (41, 50): 'Layer Mash',
            (51, 60): 'Layer Mash',
            (61, 72): 'Layer Mash',
        }
        
        for week_start, week_end, daily_feed, expected_weight, expected_eggs in layer_guides:
            key = (week_start, week_end)
            feed_type_name = feed_type_map.get(key, 'Layer Mash')
            feed_type = feed_types.get(feed_type_name) if not dry_run else None
            
            if dry_run:
                self.stdout.write(f'  Would create: Week {week_start}-{week_end}: {daily_feed}g/day, {expected_weight}kg')
                continue
            
            guide, created = FeedingGuide.objects.get_or_create(
                bird_type='LAYERS',
                week_start=week_start,
                week_end=week_end,
                defaults={
                    'feed_type': feed_type,
                    'daily_feed_per_bird_grams': daily_feed,
                    'expected_weight_kg': expected_weight,
                    'expected_egg_production': expected_eggs,
                    'notes': f'Layer week {week_start}-{week_end} - Standard layer feeding program'
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✅ Created: Week {week_start}-{week_end}: {daily_feed}g/day'))
            else:
                self.stdout.write(f'  ⚠️ Already exists: Week {week_start}-{week_end}')
    
    def create_kuroiler_guides(self, feed_types, dry_run):
        """Create feeding guides for Kuroilers"""
        self.stdout.write(self.style.SUCCESS('\n📋 Creating Kuroiler feeding guides...'))
        
        kuroiler_guides = [
            # Week Start, Week End, Daily Feed (g), Expected Weight (kg), Expected Eggs (per 100 birds)
            (1, 4, 20, 0.15, None),
            (5, 8, 35, 0.40, None),
            (9, 12, 55, 0.80, None),
            (13, 16, 75, 1.20, None),
            (17, 20, 85, 1.50, 30),
            (21, 30, 95, 1.70, 45),
            (31, 40, 100, 1.85, 50),
            (41, 50, 105, 1.95, 45),
        ]
        
        feed_type_map = {
            (1, 4): 'Kuroiler Starter',
            (5, 8): 'Kuroiler Starter',
            (9, 12): 'Kuroiler Grower',
            (13, 16): 'Kuroiler Grower',
            (17, 20): 'Kuroiler Finisher',
            (21, 30): 'Kuroiler Finisher',
            (31, 40): 'Kuroiler Finisher',
            (41, 50): 'Kuroiler Finisher',
        }
        
        for week_start, week_end, daily_feed, expected_weight, expected_eggs in kuroiler_guides:
            key = (week_start, week_end)
            feed_type_name = feed_type_map.get(key, 'Kuroiler Finisher')
            feed_type = feed_types.get(feed_type_name) if not dry_run else None
            
            if dry_run:
                self.stdout.write(f'  Would create: Week {week_start}-{week_end}: {daily_feed}g/day, {expected_weight}kg')
                continue
            
            guide, created = FeedingGuide.objects.get_or_create(
                bird_type='KUROILERS',
                week_start=week_start,
                week_end=week_end,
                defaults={
                    'feed_type': feed_type,
                    'daily_feed_per_bird_grams': daily_feed,
                    'expected_weight_kg': expected_weight,
                    'expected_egg_production': expected_eggs,
                    'notes': f'Kuroiler week {week_start}-{week_end} - Dual purpose feeding program'
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✅ Created: Week {week_start}-{week_end}: {daily_feed}g/day'))
            else:
                self.stdout.write(f'  ⚠️ Already exists: Week {week_start}-{week_end}')
    
    def print_summary(self, bird_type, dry_run):
        """Print summary of created guides"""
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*60))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  DRY RUN - No actual changes were made\n'))
        
        # Count guides by bird type
        if bird_type == 'ALL' or bird_type == 'BROILERS':
            broiler_count = FeedingGuide.objects.filter(bird_type='BROILERS').count()
            self.stdout.write(f'🐔 Broilers: {broiler_count} feeding guides')
        
        if bird_type == 'ALL' or bird_type == 'LAYERS':
            layer_count = FeedingGuide.objects.filter(bird_type='LAYERS').count()
            self.stdout.write(f'🥚 Layers: {layer_count} feeding guides')
        
        if bird_type == 'ALL' or bird_type == 'KUROILERS':
            kuroiler_count = FeedingGuide.objects.filter(bird_type='KUROILERS').count()
            self.stdout.write(f'🐓 Kuroilers: {kuroiler_count} feeding guides')
        
        feed_type_count = FeedType.objects.filter(is_active=True).count()
        category_count = FeedCategory.objects.count()
        
        self.stdout.write(f'\n📦 Feed Types: {feed_type_count}')
        self.stdout.write(f'📁 Categories: {category_count}')
        
        total_guides = FeedingGuide.objects.count()
        self.stdout.write(self.style.SUCCESS(f'\n✅ Total feeding guides: {total_guides}'))
        
        self.stdout.write(self.style.SUCCESS('\n🎉 Feeding guide creation complete!'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))


def create_feeding_guides():
    """Function to call from other scripts"""
    from django.core.management import call_command
    call_command('create_feeding_guides')