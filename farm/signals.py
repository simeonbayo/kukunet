# farm/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from datetime import timedelta
from .models import (FlockBatch,DailyRecord, FeedConsumption, FeedInventory,
                     )

@receiver(post_save, sender=FlockBatch)
@receiver(post_delete, sender=FlockBatch)
def update_house_population(sender, instance, **kwargs):
    """Update house population when flock is saved or deleted"""
    if instance.house:
        # The property will recalculate automatically
        # Just save the house to trigger any updates
        instance.house.save()

@receiver(post_save, sender=DailyRecord)
def sync_daily_record_to_feed_consumption(sender, instance, created, **kwargs):
    """Automatically sync daily record feed data to feed consumption"""
    if instance.feed_consumed_kg > 0:
        instance.sync_feed_consumption()
        instance.calculate_fcr_from_record()
        
        # Generate feed alerts based on consumption vs recommended
        from .models import FeedingGuide, FeedConsumptionAlert
        
        age_weeks = instance.batch.age_weeks
        bird_count = instance.opening_bird_count
        
        # Get feeding guide for current age
        guide = FeedingGuide.objects.filter(
            bird_type=instance.batch.bird_type,
            week_start__lte=age_weeks,
            week_end__gte=age_weeks
        ).first()
        
        if guide:
            recommended_daily_kg = (guide.daily_feed_per_bird_grams * bird_count) / 1000
            actual_consumption = instance.feed_consumed_kg
            
            # Check if consumption deviates significantly
            variance_percent = abs((actual_consumption - recommended_daily_kg) / recommended_daily_kg * 100) if recommended_daily_kg > 0 else 0
            
            if variance_percent > 15:
                severity = 'CRITICAL' if variance_percent > 30 else 'WARNING'
                alert_type = 'Overfeeding' if actual_consumption > recommended_daily_kg else 'Underfeeding'
                
                FeedConsumptionAlert.objects.create(
                    batch=instance.batch,
                    alert_date=instance.date,
                    severity=severity,
                    title=f'{alert_type} Alert - Week {age_weeks}',
                    message=f'Feed consumption is {variance_percent:.1f}% {alert_type.lower()} recommended amount.',
                    recommended_feed_kg=recommended_daily_kg,
                    current_consumption_kg=actual_consumption,
                    recommended_per_bird_grams=int(guide.daily_feed_per_bird_grams),
                    current_per_bird_grams=int((actual_consumption / bird_count) * 1000) if bird_count > 0 else 0,
                    bird_count=bird_count,
                    week_number=age_weeks
                )


@receiver(post_save, sender=FeedConsumption)
def update_daily_record_from_feed_consumption(sender, instance, created, **kwargs):
    """Update daily record when feed consumption is saved directly"""
    if instance.daily_record:
        daily = instance.daily_record
        daily.feed_consumed_kg = instance.total_daily_consumption
        daily.feed_cost = instance.daily_cost
        daily.save(update_fields=['feed_consumed_kg', 'feed_cost'])