# farm/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid

class Farm(models.Model):
    """Main farm model"""
    FARM_TYPES = [
        ('LAYERS', 'Layers'),
        ('BROILERS', 'Broilers'),
        ('BREEDERS', 'Breeders'),
        ('MIXED', 'Mixed'),
        ('FREE_RANGE', 'Free Range'),
    ]
    
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='farms')
    farm_name = models.CharField(max_length=100)
    farm_type = models.CharField(max_length=20, choices=FARM_TYPES, default='LAYERS')
    registration_number = models.CharField(max_length=50, blank=True, unique=True)
    
    # Location
    district = models.CharField(max_length=100)
    village = models.CharField(max_length=100)
    parish = models.CharField(max_length=100, blank=True)
    gps_coordinates = models.CharField(max_length=100, blank=True, help_text="Latitude, Longitude")
    
    # Farm Details
    size_acres = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    established_date = models.DateField(null=True, blank=True)
    
    # Contact
    contact_phone = models.CharField(max_length=15, blank=True)
    contact_email = models.EmailField(blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Metadata
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='created_farms')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['tenant', 'farm_name']
    
    def __str__(self):
        return self.farm_name
    
    @property
    def total_birds(self):
        return self.houses.aggregate(total=models.Sum('current_population'))['total'] or 0
    
    @property
    def active_flocks(self):
        return self.flock_batches.filter(status='ACTIVE').count()


class House(models.Model):
    """Poultry house/pen model"""
    HOUSE_TYPES = [
        ('OPEN', 'Open House'),
        ('CLOSED', 'Closed House'),
        ('BATTERY', 'Battery Cages'),
        ('DEEP_LITTER', 'Deep Litter'),
    ]
    
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='houses')
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='houses')
    house_number = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    house_type = models.CharField(max_length=20, choices=HOUSE_TYPES, default='OPEN')
    
    # Capacity
    capacity = models.IntegerField(validators=[MinValueValidator(1)])
    
    
    # Dimensions
    length_m = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    width_m = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    height_m = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    area_sqft = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Equipment
    has_automated_feeder = models.BooleanField(default=False)
    has_automated_drinker = models.BooleanField(default=False)
    has_ventilation = models.BooleanField(default=False)
    has_heating = models.BooleanField(default=False)
    has_lighting = models.BooleanField(default=False)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['farm', 'house_number']
        ordering = ['house_number']
    
    def __str__(self):
        return f"{self.farm.farm_name} - {self.name}"
    
    @property
    def current_population(self):
        """Calculate current population from active flocks in this house"""
        return self.flock_batches.filter(status='ACTIVE').aggregate(
            total=models.Sum('current_quantity')
        )['total'] or 0
    
    @property
    def occupancy_rate(self):
        """Calculate occupancy rate"""
        if self.capacity > 0:
            return (self.current_population / self.capacity) * 100
        return 0


class FlockBatch(models.Model):
    """Flock batch management"""
    STATUS_CHOICES = [
        ('PLANNED', 'Planned'),
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('CULLED', 'Culled'),
        ('DEPLETED', 'Depleted'),
        ('SICK', 'Sick/Quarantined'),
    ]
    
    BIRD_TYPES = [
        ('LAYERS', 'Layers'),
        ('BROILERS', 'Broilers'),
        ('DAY_OLD', 'Day Old Chicks'),
        ('GROWERS', 'Growers'),
        ('BREEDERS', 'Breeders'),
        ('KUROILER', 'Kuroiler'),
        ('POINTS', 'Point of Lay'),
    ]
    
    BREEDS = [
        ('ISA_BROWN', 'ISA Brown'),
        ('BOVANS_BROWN', 'Bovans Brown'),
        ('HYLINE', 'Hy-Line'),
        ('LOHMANN', 'Lohmann'),
        ('ROSS', 'Ross'),
        ('COBB', 'Cobb'),
        ('KUROILER', 'Kuroiler'),
        ('RAINBOW', 'Rainbow Rooster'),
        ('LOCAL', 'Local Breed'),
        ('OTHER', 'Other'),
    ]
    
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='flock_batches')
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='flock_batches')
    house = models.ForeignKey(House, on_delete=models.CASCADE, related_name='flock_batches', null=True, blank=True)
    
    # Basic Info
    batch_number = models.CharField(max_length=50, unique=True, blank=True)
    batch_name = models.CharField(max_length=100)
    bird_type = models.CharField(max_length=20, choices=BIRD_TYPES)
    breed = models.CharField(max_length=30, choices=BREEDS, default='ISA_BROWN')
    
    # Quantity
    initial_quantity = models.IntegerField(validators=[MinValueValidator(1)], default=1)
    current_quantity = models.IntegerField(default=0)
    
    # Dates
    start_date = models.DateField()
    expected_end_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    # Source
    source = models.CharField(max_length=200, blank=True, help_text="Where birds were purchased from")
    cost_per_bird = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Performance Metrics
    expected_egg_production = models.IntegerField(default=0, help_text="Expected eggs per day")
    expected_feed_conversion = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    expected_mortality_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLANNED')
    notes = models.TextField(blank=True)
    
    # Metadata
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='created_flocks')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['batch_number']),
            models.Index(fields=['start_date']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.batch_number:
            self.batch_number = f"BATCH-{uuid.uuid4().hex[:8].upper()}"
        if self.current_quantity == 0:
            self.current_quantity = self.initial_quantity
        self.total_cost = self.initial_quantity * self.cost_per_bird
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.batch_name} ({self.batch_number})"
    
    @property
    def age_days(self):
        return (timezone.now().date() - self.start_date).days
    
    @property
    def age_weeks(self):
        return self.age_days // 7
    
    @property
    def total_mortality(self):
        return self.daily_records.aggregate(total=models.Sum('mortality'))['total'] or 0
    
    @property
    def mortality_rate(self):
        if self.initial_quantity > 0:
            return (self.total_mortality / self.initial_quantity) * 100
        return 0
    
    @property
    def survival_rate(self):
        return 100 - self.mortality_rate
    
    @property
    def total_feed_consumed(self):
        return self.daily_records.aggregate(total=models.Sum('feed_consumed_kg'))['total'] or 0
    
    @property
    def total_eggs_produced(self):
        return self.daily_records.aggregate(total=models.Sum('eggs_collected'))['total'] or 0
    
    @property
    def avg_daily_eggs(self):
        days = self.age_days
        if days > 0:
            return self.total_eggs_produced / days
        return 0
    
    @property
    def feed_conversion_ratio(self):
        if self.total_eggs_produced > 0:
            return float(self.total_feed_consumed) / self.total_eggs_produced
        return 0


# farm/models.py - Complete DailyRecord model

class DailyRecord(models.Model):
    """Complete daily records for all poultry types with feed management integration"""
    
    HEALTH_STATUS = [
        ('GOOD', 'Good - No Issues'),
        ('WATCH', 'Watch - Monitor Closely'),
        ('MINOR', 'Minor Illness'),
        ('SERIOUS', 'Serious Illness'),
        ('OUTBREAK', 'Disease Outbreak'),
    ]
    
    LITTER_CONDITION = [
        ('DRY', 'Dry - Good'),
        ('DAMP', 'Damp - Needs Attention'),
        ('WET', 'Wet - Change Required'),
        ('POOR', 'Poor - Immediate Action'),
    ]
    
    VENTILATION_STATUS = [
        ('GOOD', 'Good'),
        ('POOR', 'Poor'),
        ('EXCESSIVE', 'Excessive'),
        ('INSUFFICIENT', 'Insufficient'),
    ]
    
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='daily_records')
    batch = models.ForeignKey(FlockBatch, on_delete=models.CASCADE, related_name='daily_records')
    
    # ========== DATE ==========
    date = models.DateField(default=timezone.now)
    
    # ========== FLOCK INFORMATION ==========
    opening_bird_count = models.IntegerField(default=0)
    birds_added = models.IntegerField(default=0)
    mortality = models.IntegerField(default=0)
    birds_sold = models.IntegerField(default=0)
    birds_culled = models.IntegerField(default=0)
    closing_bird_count = models.IntegerField(default=0)
    
    # ========== FEED RECORD ==========
    feed_type = models.CharField(max_length=50, blank=True, choices=[
        ('STARTER', 'Starter Feed (0-4 weeks)'),
        ('GROWER', 'Grower Feed (4-16 weeks)'),
        ('FINISHER', 'Finisher Feed (16+ weeks)'),
        ('LAYER_MASH', 'Layer Mash'),
        ('BROILER_STARTER', 'Broiler Starter'),
        ('BROILER_FINISHER', 'Broiler Finisher'),
        ('CHICK_MASH', 'Chick Mash'),
        ('OTHER', 'Other'),
    ])
    feed_given_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    feed_remaining_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    feed_consumed_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # ========== FEED MANAGEMENT INTEGRATION ==========
    # Only keep this field - remove feed_consumption_record (it's defined in FeedConsumption model)
    feed_type_obj = models.ForeignKey('FeedType', on_delete=models.SET_NULL, null=True, blank=True, related_name='daily_records')
    
    # ========== WATER CONSUMPTION ==========
    water_provided_liters = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    water_consumed_liters = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # ========== HEALTH RECORD ==========
    health_status = models.CharField(max_length=20, choices=HEALTH_STATUS, default='GOOD')
    signs_observed = models.TextField(blank=True)
    disease_symptoms = models.TextField(blank=True)
    treatments_given = models.TextField(blank=True)
    deworming_done = models.BooleanField(default=False)
    deworming_product = models.CharField(max_length=100, blank=True)
    veterinary_visit = models.BooleanField(default=False)
    veterinary_notes = models.TextField(blank=True)
    
    # ========== MEDICATION RECORD ==========
    drug_name = models.CharField(max_length=100, blank=True)
    dosage = models.CharField(max_length=100, blank=True)
    purpose = models.CharField(max_length=200, blank=True)
    withdrawal_period_days = models.IntegerField(default=0)
    administered_by = models.CharField(max_length=100, blank=True)
    
    # ========== ENVIRONMENTAL RECORD ==========
    temperature_c = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    humidity_percent = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    ventilation_status = models.CharField(max_length=20, choices=VENTILATION_STATUS, default='GOOD')
    litter_condition = models.CharField(max_length=20, choices=LITTER_CONDITION, default='DRY')
    ammonia_level = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # ========== BROILER SPECIFIC ==========
    weight_sample_count = models.IntegerField(default=0)
    avg_weight_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    min_weight_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    max_weight_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    feed_conversion_ratio = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    weight_gain_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    
    # ========== LAYER SPECIFIC ==========
    eggs_collected = models.IntegerField(default=0)
    eggs_broken = models.IntegerField(default=0)
    eggs_dirty = models.IntegerField(default=0)
    eggs_cracked = models.IntegerField(default=0)
    eggs_saleable = models.IntegerField(default=0)
    eggs_small = models.IntegerField(default=0)
    eggs_medium = models.IntegerField(default=0)
    eggs_large = models.IntegerField(default=0)
    eggs_extra_large = models.IntegerField(default=0)
    egg_production_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # ========== SALES RECORD ==========
    birds_sold_count = models.IntegerField(default=0)
    birds_sold_avg_weight = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    price_per_bird = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_per_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    trays_sold = models.IntegerField(default=0)
    eggs_sold_count = models.IntegerField(default=0)
    price_per_tray = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_per_egg = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    sales_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # ========== EXPENSES ==========
    feed_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    medication_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vaccine_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    labour_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    transport_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    utilities_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_expenses = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # ========== NOTES ==========
    farmer_observations = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    alerts_generated = models.JSONField(default=list)
    
    # ========== METADATA ==========
    recorded_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['batch', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['batch', 'date']),
        ]
    
    def save(self, *args, **kwargs):
        from decimal import Decimal
        
        # Calculate closing bird count
        if self.opening_bird_count > 0:
            self.closing_bird_count = (
                self.opening_bird_count + self.birds_added - 
                self.mortality - self.birds_sold - self.birds_culled
            )
            # Update batch current quantity
            self.batch.current_quantity = self.closing_bird_count
            self.batch.save()
        
        # Calculate feed consumed using Decimal
        if self.feed_given_kg > 0 and self.feed_remaining_kg >= 0:
            self.feed_consumed_kg = Decimal(str(self.feed_given_kg)) - Decimal(str(self.feed_remaining_kg))
        
        # Calculate saleable eggs
        self.eggs_saleable = (
            self.eggs_collected - self.eggs_broken - 
            self.eggs_dirty - self.eggs_cracked
        )
        
        # Calculate egg production percentage
        if self.batch.bird_type in ['LAYERS', 'KUROILER'] and self.opening_bird_count > 0:
            self.egg_production_percent = (Decimal(str(self.eggs_collected)) / Decimal(str(self.opening_bird_count))) * 100
        
        # Calculate sales revenue using Decimal
        self.sales_revenue = (
            (Decimal(str(self.birds_sold_count)) * Decimal(str(self.price_per_bird))) +
            (Decimal(str(self.eggs_sold_count)) * Decimal(str(self.price_per_egg))) +
            (Decimal(str(self.trays_sold)) * Decimal(str(self.price_per_tray)))
        )
        
        # Calculate total expenses using Decimal
        self.total_expenses = (
            Decimal(str(self.feed_cost)) + Decimal(str(self.medication_cost)) + 
            Decimal(str(self.vaccine_cost)) + Decimal(str(self.labour_cost)) + 
            Decimal(str(self.transport_cost)) + Decimal(str(self.utilities_cost)) + 
            Decimal(str(self.other_cost))
        )
        
        # Generate alerts
        self.alerts_generated = self.generate_alerts()
        
        super().save(*args, **kwargs)
        
        # Sync with feed management system
        self.sync_feed_consumption()
        
        # Calculate FCR if weight data available
        self.calculate_fcr_from_record()
    
    def sync_feed_consumption(self):
        """Sync daily record feed data to FeedConsumption model - creates separate records for each feeding time"""
        from decimal import Decimal
        
        if self.feed_consumed_kg > 0:
            # Get or create feed type object
            feed_type_name = self.get_feed_type_display() if self.feed_type else "Other"
            feed_type, _ = FeedType.objects.get_or_create(
                name=feed_type_name,
                defaults={'feed_stage': 'OTHER', 'is_active': True}
            )
            self.feed_type_obj = feed_type
            
            # Get inventory average cost
            inventory = FeedInventory.objects.filter(tenant=self.tenant, feed_type=feed_type).first()
            
            # Split consumption into three feeding times (approximate distribution)
            # If feed was given, distribute based on typical feeding patterns
            if self.feed_given_kg > 0:
                morning_amount = self.feed_consumed_kg * Decimal('0.4')  # 40% in morning
                afternoon_amount = self.feed_consumed_kg * Decimal('0.4')  # 40% in afternoon
                evening_amount = self.feed_consumed_kg * Decimal('0.2')  # 20% in evening
            else:
                morning_amount = self.feed_consumed_kg
                afternoon_amount = Decimal('0')
                evening_amount = Decimal('0')
            
            # Create or update morning feeding record
            if morning_amount > 0:
                FeedConsumption.objects.update_or_create(
                    batch=self.batch,
                    date=self.date,
                    feeding_time='MORNING',
                    defaults={
                        'tenant': self.tenant,
                        'daily_record': self,
                        'feed_type': feed_type,
                        'feed_amount_kg': morning_amount,
                        'feed_given_kg': self.feed_given_kg * Decimal('0.4') if self.feed_given_kg > 0 else Decimal('0'),
                        'feed_remaining_kg': Decimal('0'),
                        'bird_count': self.opening_bird_count,
                        'feed_per_bird_grams': (morning_amount / Decimal(str(self.opening_bird_count))) * 1000 if self.opening_bird_count > 0 else Decimal('0'),
                        'notes': f"Morning feeding - {self.farmer_observations[:200] if self.farmer_observations else ''}",
                        'recorded_by': self.recorded_by
                    }
                )
            
            # Create or update afternoon feeding record
            if afternoon_amount > 0:
                FeedConsumption.objects.update_or_create(
                    batch=self.batch,
                    date=self.date,
                    feeding_time='AFTERNOON',
                    defaults={
                        'tenant': self.tenant,
                        'daily_record': self,
                        'feed_type': feed_type,
                        'feed_amount_kg': afternoon_amount,
                        'feed_given_kg': self.feed_given_kg * Decimal('0.4') if self.feed_given_kg > 0 else Decimal('0'),
                        'feed_remaining_kg': Decimal('0'),
                        'bird_count': self.opening_bird_count,
                        'feed_per_bird_grams': (afternoon_amount / Decimal(str(self.opening_bird_count))) * 1000 if self.opening_bird_count > 0 else Decimal('0'),
                        'notes': f"Afternoon feeding - {self.farmer_observations[:200] if self.farmer_observations else ''}",
                        'recorded_by': self.recorded_by
                    }
                )
            
            # Create or update evening feeding record
            if evening_amount > 0:
                FeedConsumption.objects.update_or_create(
                    batch=self.batch,
                    date=self.date,
                    feeding_time='EVENING',
                    defaults={
                        'tenant': self.tenant,
                        'daily_record': self,
                        'feed_type': feed_type,
                        'feed_amount_kg': evening_amount,
                        'feed_given_kg': self.feed_given_kg * Decimal('0.2') if self.feed_given_kg > 0 else Decimal('0'),
                        'feed_remaining_kg': Decimal('0'),
                        'bird_count': self.opening_bird_count,
                        'feed_per_bird_grams': (evening_amount / Decimal(str(self.opening_bird_count))) * 1000 if self.opening_bird_count > 0 else Decimal('0'),
                        'notes': f"Evening feeding - {self.farmer_observations[:200] if self.farmer_observations else ''}",
                        'recorded_by': self.recorded_by
                    }
                )
            
            # Update inventory
            self.update_feed_inventory()
    
    def update_feed_inventory(self):
        """Update feed inventory based on consumption"""
        from decimal import Decimal
        
        if self.feed_consumed_kg > 0 and self.feed_type_obj:
            inventory, created = FeedInventory.objects.get_or_create(
                tenant=self.tenant,
                feed_type=self.feed_type_obj,
                defaults={'current_stock_kg': Decimal('0'), 'is_active': True}
            )
            
            current = Decimal(str(inventory.current_stock_kg))
            consumed = Decimal(str(self.feed_consumed_kg))
            inventory.current_stock_kg = current - consumed
            inventory.save()
            
            # Check and create low stock alert
            if inventory.is_low_stock:
                from .models import FeedConsumptionAlert
                FeedConsumptionAlert.objects.get_or_create(
                    batch=self.batch,
                    title='Low Feed Stock Alert',
                    alert_date=self.date,
                    defaults={
                        'severity': 'WARNING',
                        'message': f'{self.feed_type_obj.name} stock is low ({inventory.current_stock_kg:.1f} kg remaining). Please reorder.',
                        'recommended_feed_kg': inventory.reorder_level_kg,
                        'current_consumption_kg': inventory.current_stock_kg,
                        'week_number': self.batch.age_weeks,
                        'bird_count': self.opening_bird_count
                    }
                )
    
    def calculate_fcr_from_record(self):
        """Calculate Feed Conversion Ratio from daily record"""
        from decimal import Decimal
        
        if self.avg_weight_kg and self.feed_consumed_kg > 0 and self.opening_bird_count > 0:
            # Weight gain = current avg weight - previous avg weight
            previous_record = DailyRecord.objects.filter(
                batch=self.batch, 
                date__lt=self.date
            ).order_by('-date').first()
            
            if previous_record and previous_record.avg_weight_kg:
                weight_gain = Decimal(str(self.avg_weight_kg)) - Decimal(str(previous_record.avg_weight_kg))
                total_weight_gain = weight_gain * Decimal(str(self.opening_bird_count))
                if total_weight_gain > 0:
                    self.feed_conversion_ratio = Decimal(str(self.feed_consumed_kg)) / total_weight_gain
                self.weight_gain_kg = weight_gain
            else:
                # For first record, estimate based on breed standard
                self.feed_conversion_ratio = Decimal('0')
            
            # Save again with calculated FCR
            DailyRecord.objects.filter(id=self.id).update(
                feed_conversion_ratio=self.feed_conversion_ratio,
                weight_gain_kg=self.weight_gain_kg
            )
        
        return self.feed_conversion_ratio
    
    def generate_alerts(self):
        from decimal import Decimal
        
        alerts = []
        
        # High mortality alert
        if self.mortality > 5:
            alerts.append({
                'type': 'HIGH_MORTALITY',
                'message': f'High mortality: {self.mortality} birds died today',
                'severity': 'CRITICAL'
            })
        elif self.mortality > 2:
            alerts.append({
                'type': 'MORTALITY',
                'message': f'{self.mortality} birds died today',
                'severity': 'WARNING'
            })
        
        # Low water consumption alert
        if self.water_consumed_liters > 0 and self.opening_bird_count > 0:
            avg_water = float(self.water_consumed_liters) / self.opening_bird_count
            if avg_water < 0.2:
                alerts.append({
                    'type': 'LOW_WATER',
                    'message': 'Water consumption is unusually low',
                    'severity': 'URGENT'
                })
        
        # Poor litter condition alert
        if self.litter_condition in ['WET', 'POOR']:
            alerts.append({
                'type': 'POOR_LITTER',
                'message': f'Litter condition is {self.litter_condition}',
                'severity': 'HIGH'
            })
        
        # Low egg production alert for layers
        if self.batch.bird_type in ['LAYERS', 'KUROILER'] and self.egg_production_percent:
            if self.egg_production_percent < 60:
                alerts.append({
                    'type': 'LOW_PRODUCTION',
                    'message': f'Egg production dropped to {self.egg_production_percent:.1f}%',
                    'severity': 'HIGH'
                })
        
        # Feed consumption alert - Compare with feeding guide
        from .models import FeedingGuide, FeedConsumptionAlert
        age_weeks = self.batch.age_weeks
        guide = FeedingGuide.objects.filter(
            bird_type=self.batch.bird_type,
            week_start__lte=age_weeks,
            week_end__gte=age_weeks
        ).first()
        
        if guide and self.feed_consumed_kg > 0:
            recommended_daily_kg = (float(guide.daily_feed_per_bird_grams) * self.opening_bird_count) / 1000
            current_consumption = float(self.feed_consumed_kg)
            variance_percent = abs((current_consumption - recommended_daily_kg) / recommended_daily_kg * 100) if recommended_daily_kg > 0 else 0
            
            if variance_percent > 15:
                severity = 'CRITICAL' if variance_percent > 30 else 'WARNING'
                alert_type = 'Overfeeding' if current_consumption > recommended_daily_kg else 'Underfeeding'
                alerts.append({
                    'type': f'{alert_type.upper()}_ALERT',
                    'message': f'{alert_type} detected: {variance_percent:.1f}% deviation from recommended feed amount',
                    'severity': severity
                })
                
                # Create feed consumption alert record
                FeedConsumptionAlert.objects.get_or_create(
                    batch=self.batch,
                    alert_date=self.date,
                    title=f'{alert_type} Alert - Week {age_weeks}',
                    defaults={
                        'severity': severity,
                        'message': f'Feed consumption is {variance_percent:.1f}% {alert_type.lower()} recommended amount.',
                        'recommended_feed_kg': recommended_daily_kg,
                        'current_consumption_kg': current_consumption,
                        'recommended_per_bird_grams': int(guide.daily_feed_per_bird_grams),
                        'current_per_bird_grams': int((current_consumption / self.opening_bird_count) * 1000) if self.opening_bird_count > 0 else 0,
                        'bird_count': self.opening_bird_count,
                        'week_number': age_weeks
                    }
                )
        
        return alerts
    
    def __str__(self):
        return f"{self.batch.batch_name} - {self.date}"

class VaccinationSchedule(models.Model):
    """Predefined vaccination schedules"""
    BIRD_TYPES = [
        ('LAYERS', 'Layers'),
        ('BROILERS', 'Broilers'),
        ('KUROILERS', 'Kuroilers'),
        ('BREEDERS', 'Breeders'),
    ]
    
    VACCINE_TYPES = [
        ('NEWCASTLE', 'Newcastle Disease (ND)'),
        ('INFECTIOUS_BRONCHITIS', 'Infectious Bronchitis (IB)'),
        ('GUMBORO', 'Gumboro (IBD)'),
        ('FOWL_POX', 'Fowl Pox (FP)'),
        ('SALMONELLA', 'Salmonella'),
        ('COCCIDIOSIS', 'Coccidiosis'),
        ('MAREKS', "Marek's Disease"),
        ('EGG_DROP_SYNDROME', 'Egg Drop Syndrome'),
        ('OTHER', 'Other'),
    ]
    
    bird_type = models.CharField(max_length=20, choices=BIRD_TYPES)
    week_number = models.IntegerField()
    vaccine_name = models.CharField(max_length=100)
    vaccine_type = models.CharField(max_length=30, choices=VACCINE_TYPES)
    administration_method = models.CharField(max_length=50)
    dosage = models.CharField(max_length=100, blank=True)
    is_required = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['bird_type', 'week_number']
        unique_together = ['bird_type', 'week_number', 'vaccine_type']
    
    def __str__(self):
        return f"{self.get_bird_type_display()} - Week {self.week_number}: {self.vaccine_name}"


class VaccinationRecord(models.Model):
    """Vaccination tracking"""
    ADMINISTRATION_METHODS = [
        ('DRINKING_WATER', 'Drinking Water'),
        ('SPRAY', 'Spray'),
        ('INJECTION', 'Injection'),
        ('EYE_DROP', 'Eye Drop'),
        ('WING_WEB', 'Wing Web'),
    ]
    
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('COMPLETED', 'Completed'),
        ('MISSED', 'Missed'),
        ('RESCHEDULED', 'Rescheduled'),
    ]
    
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='vaccinations')
    batch = models.ForeignKey(FlockBatch, on_delete=models.CASCADE, related_name='vaccinations')
    
    
    vaccine_type = models.CharField(max_length=30, choices=VaccinationSchedule.VACCINE_TYPES)
    manufacturer = models.CharField(max_length=100, blank=True)
    batch_number = models.CharField(max_length=50, blank=True)
    
    scheduled_date = models.DateField()
    administered_date = models.DateField(null=True, blank=True)
    administration_method = models.CharField(max_length=20, choices=ADMINISTRATION_METHODS, default='DRINKING_WATER')
    dosage = models.CharField(max_length=50, blank=True)
    quantity_used = models.IntegerField(default=0)
    
    cost_per_dose = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    administered_by = models.CharField(max_length=100, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    notes = models.TextField(blank=True)
    reaction_notes = models.TextField(blank=True)
    
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['scheduled_date']
    
    def __str__(self):
        return f"{self.vaccine_name} - {self.batch.batch_name}"


class FlockVaccinationSchedule(models.Model):
    """Vaccination schedule for a specific flock"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('OVERDUE', 'Overdue'),
        ('SKIPPED', 'Skipped'),
    ]
    
    batch = models.ForeignKey(FlockBatch, on_delete=models.CASCADE, related_name='vaccination_schedule')
    vaccine_template = models.ForeignKey(VaccinationSchedule, on_delete=models.CASCADE)
    scheduled_date = models.DateField()
    due_week = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    completed_date = models.DateField(null=True, blank=True)
    vaccination_record = models.OneToOneField(VaccinationRecord, on_delete=models.SET_NULL, null=True, blank=True)
    notification_sent = models.BooleanField(default=False)
    reminder_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['scheduled_date']
        unique_together = ['batch', 'vaccine_template']
    
    def __str__(self):
        return f"{self.batch.batch_name} - {self.vaccine_template.vaccine_name}"


def generate_vaccination_schedule_for_batch(batch):
    """Generate vaccination schedule when a new batch is created"""
    bird_type_map = {
        'LAYERS': 'LAYERS',
        'BROILERS': 'BROILERS',
        'DAY_OLD': 'BROILERS',
        'KUROILER': 'KUROILERS',
        'BREEDERS': 'BREEDERS',
    }
    
    bird_type = bird_type_map.get(batch.bird_type, 'LAYERS')
    templates = VaccinationSchedule.objects.filter(bird_type=bird_type)
    
    schedules = []
    for template in templates:
        scheduled_date = batch.start_date + timezone.timedelta(weeks=template.week_number)
        schedule = FlockVaccinationSchedule.objects.create(
            batch=batch,
            vaccine_template=template,
            scheduled_date=scheduled_date,
            due_week=template.week_number
        )
        schedules.append(schedule)
    
    return schedules

class HealthRecord(models.Model):
    """Health monitoring records for flocks"""
    
    HEALTH_STATUS = [
        ('EXCELLENT', 'Excellent - No Issues'),
        ('GOOD', 'Good - Minor Observations'),
        ('FAIR', 'Fair - Needs Attention'),
        ('POOR', 'Poor - Health Issues'),
        ('CRITICAL', 'Critical - Immediate Action Required'),
    ]
    
    DISEASE_TYPES = [
        ('RESPIRATORY', 'Respiratory Disease'),
        ('DIGESTIVE', 'Digestive Issue'),
        ('EGG_DROP', 'Egg Drop Syndrome'),
        ('LAMENESS', 'Lameness/Leg Issues'),
        ('SKIN', 'Skin/Feather Issues'),
        ('EYE', 'Eye Infection'),
        ('NEWCASTLE', 'Newcastle Disease'),
        ('GUMBORO', 'Gumboro (IBD)'),
        ('FOWL_POX', 'Fowl Pox'),
        ('COCCIDIOSIS', 'Coccidiosis'),
        ('SALMONELLA', 'Salmonella'),
        ('AVIAN_FLU', 'Avian Influenza'),
        ('UNKNOWN', 'Unknown/Under Investigation'),
        ('OTHER', 'Other'),
    ]
    
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='health_records')
    batch = models.ForeignKey(FlockBatch, on_delete=models.CASCADE, related_name='health_records')
    
    # Record Date
    record_date = models.DateField(default=timezone.now)
    
    # Health Status
    health_status = models.CharField(max_length=20, choices=HEALTH_STATUS, default='GOOD')
    disease_type = models.CharField(max_length=30, choices=DISEASE_TYPES, blank=True)
    
    # Symptoms Observed
    symptoms = models.TextField(blank=True, help_text="List of observed symptoms")
    affected_birds_count = models.IntegerField(default=0, help_text="Number of birds showing symptoms")
    affected_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Physical Signs
    reduced_feed_intake = models.BooleanField(default=False)
    reduced_water_intake = models.BooleanField(default=False)
    respiratory_distress = models.BooleanField(default=False)
    diarrhea = models.BooleanField(default=False)
    swollen_eyes = models.BooleanField(default=False)
    lethargy = models.BooleanField(default=False)
    sudden_death = models.BooleanField(default=False)
    
    # Environmental Factors
    temperature_c = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    humidity_percent = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    ammonia_level = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    litter_condition = models.CharField(max_length=20, choices=DailyRecord.LITTER_CONDITION, default='DRY')
    
    # Notes
    observations = models.TextField(blank=True)
    vet_recommendations = models.TextField(blank=True)
    
    # Metadata
    recorded_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='health_records')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-record_date']
        indexes = [
            models.Index(fields=['batch', 'record_date']),
            models.Index(fields=['health_status']),
        ]
    
    def save(self, *args, **kwargs):
        if self.affected_birds_count > 0 and self.batch.current_quantity > 0:
            self.affected_percentage = (self.affected_birds_count / self.batch.current_quantity) * 100
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.batch.batch_name} - {self.record_date} - {self.get_health_status_display()}"


class TreatmentRecord(models.Model):
    """Treatment records for sick birds"""
    
    TREATMENT_TYPES = [
        ('MEDICATION', 'Medication'),
        ('VACCINATION', 'Vaccination'),
        ('DEWORMING', 'Deworming'),
        ('ISOLATION', 'Isolation/Quarantine'),
        ('CULLING', 'Culling'),
        ('SUPPORTIVE', 'Supportive Care'),
        ('OTHER', 'Other'),
    ]
    
    ADMINISTRATION_METHODS = [
        ('DRINKING_WATER', 'Drinking Water'),
        ('FEED', 'Mixed in Feed'),
        ('INJECTION', 'Injection'),
        ('TOPICAL', 'Topical Application'),
        ('ORAL', 'Oral/Drenching'),
        ('SPRAY', 'Spray'),
    ]
    
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='treatment_records')
    batch = models.ForeignKey(FlockBatch, on_delete=models.CASCADE, related_name='treatment_records')
    health_record = models.ForeignKey(HealthRecord, on_delete=models.CASCADE, related_name='treatments', null=True, blank=True)
    
    # Treatment Details
    treatment_type = models.CharField(max_length=20, choices=TREATMENT_TYPES)
    medication_name = models.CharField(max_length=200, blank=True, help_text="Name of medication used")
    active_ingredient = models.CharField(max_length=200, blank=True)
    dosage = models.CharField(max_length=100, blank=True, help_text="Dosage amount")
    unit = models.CharField(max_length=20, blank=True, choices=[
        ('ml', 'Milliliters'),
        ('mg', 'Milligrams'),
        ('g', 'Grams'),
        ('tablet', 'Tablet'),
        ('capsule', 'Capsule'),
        ('drop', 'Drop'),
    ])
    
    # Administration
    administration_method = models.CharField(max_length=20, choices=ADMINISTRATION_METHODS, default='DRINKING_WATER')
    frequency = models.CharField(max_length=100, blank=True, help_text="e.g., Twice daily, Once daily")
    duration_days = models.IntegerField(default=1, help_text="Duration of treatment in days")
    
    # Quantities
    quantity_treated = models.IntegerField(default=0, help_text="Number of birds treated")
    total_quantity_used = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Total medication used")
    
    # Dates
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    
    # Cost
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Effectiveness
    effectiveness_rating = models.IntegerField(default=0, choices=[
        (0, 'Not Rated'),
        (1, 'Poor - No improvement'),
        (2, 'Fair - Slight improvement'),
        (3, 'Good - Moderate improvement'),
        (4, 'Very Good - Significant improvement'),
        (5, 'Excellent - Full recovery'),
    ])
    effectiveness_notes = models.TextField(blank=True)
    
    # Withdrawal Period
    withdrawal_days = models.IntegerField(default=0, help_text="Days to withdraw before sale/consumption")
    withdrawal_notes = models.TextField(blank=True)
    
    # Recovery
    birds_recovered = models.IntegerField(default=0)
    birds_died = models.IntegerField(default=0)
    recovery_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Prescription
    prescribed_by = models.CharField(max_length=200, blank=True, help_text="Veterinarian name")
    prescription_number = models.CharField(max_length=100, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Metadata
    administered_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='administered_treatments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['batch', 'start_date']),
            models.Index(fields=['treatment_type']),
        ]
    
    def save(self, *args, **kwargs):
        self.total_cost = self.total_quantity_used * self.cost_per_unit
        if self.birds_recovered + self.birds_died > 0:
            self.recovery_rate = (self.birds_recovered / (self.birds_recovered + self.birds_died)) * 100
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.batch.batch_name} - {self.treatment_type} - {self.start_date}"


class HealthAlert(models.Model):
    """Automated health alerts based on monitoring"""
    
    ALERT_TYPES = [
        ('HIGH_MORTALITY', 'High Mortality'),
        ('DISEASE_OUTBREAK', 'Disease Outbreak'),
        ('SYMPTOM_ALERT', 'Symptom Alert'),
        ('TREATMENT_DUE', 'Treatment Due'),
        ('FOLLOW_UP', 'Follow-up Required'),
        ('VET_VISIT', 'Veterinary Visit Recommended'),
    ]
    
    SEVERITY_LEVELS = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    batch = models.ForeignKey(FlockBatch, on_delete=models.CASCADE, related_name='health_alerts')
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS, default='MEDIUM')
    title = models.CharField(max_length=200)
    message = models.TextField()
    recommended_action = models.TextField(blank=True)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.batch.batch_name} - {self.alert_type}"

# ==================== FEED MANAGEMENT MODELS ====================

class FeedCategory(models.Model):
    """Categories of feed"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Feed Categories"
        ordering = ['name']


class FeedType(models.Model):
    """Types of feed (Starter, Grower, Finisher, Layer Mash, etc.)"""
    FEED_STAGES = [
        ('STARTER', 'Starter (0-4 weeks)'),
        ('GROWER', 'Grower (4-16 weeks)'),
        ('FINISHER', 'Finisher (16+ weeks)'),
        ('LAYER_MASH', 'Layer Mash'),
        ('BROILER_STARTER', 'Broiler Starter (0-3 weeks)'),
        ('BROILER_FINISHER', 'Broiler Finisher (3-6 weeks)'),
        ('CHICK_MASH', 'Chick Mash'),
        ('DUAL_PURPOSE', 'Dual Purpose Feed'),
    ]
    
    name = models.CharField(max_length=100)
    feed_stage = models.CharField(max_length=20, choices=FEED_STAGES)
    category = models.ForeignKey(FeedCategory, on_delete=models.SET_NULL, null=True)
    description = models.TextField(blank=True)
    
    # Nutritional Information
    protein_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    energy_mj_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    fat_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    fiber_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name


class FeedingGuide(models.Model):
    """Feeding guide template for different bird types and ages"""
    BIRD_TYPES = [
        ('LAYERS', 'Layers'),
        ('BROILERS', 'Broilers'),
        ('KUROILERS', 'Kuroilers'),
    ]
    
    bird_type = models.CharField(max_length=20, choices=BIRD_TYPES)
    week_start = models.IntegerField(help_text="Starting week")
    week_end = models.IntegerField(help_text="Ending week")
    feed_type = models.ForeignKey(FeedType, on_delete=models.CASCADE)
    daily_feed_per_bird_grams = models.DecimalField(max_digits=8, decimal_places=2, 
                                                     help_text="Daily feed per bird in grams")
    expected_weight_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    expected_egg_production = models.IntegerField(null=True, blank=True, help_text="Expected eggs per day per 100 birds")
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['bird_type', 'week_start']
        unique_together = ['bird_type', 'week_start', 'week_end']
    
    def __str__(self):
        return f"{self.get_bird_type_display()} - Week {self.week_start}-{self.week_end}: {self.daily_feed_per_bird_grams}g"


class FeedInventory(models.Model):
    """Feed inventory tracking"""
    UNIT_CHOICES = [
        ('KG', 'Kilograms'),
        ('BAG', 'Bag (50kg)'),
        ('TON', 'Tonnes'),
    ]
    
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='feed_inventory')
    feed_type = models.ForeignKey(FeedType, on_delete=models.CASCADE)
    batch_number = models.CharField(max_length=100, blank=True)
    
    # Stock - Use Decimal with proper defaults
    current_stock_kg = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    minimum_stock_kg = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('100.00'))
    reorder_level_kg = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('200.00'))
    
    # Purchase info
    last_purchase_date = models.DateField(null=True, blank=True)
    last_purchase_quantity_kg = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    last_purchase_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    average_cost_per_kg = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Supplier
    supplier_name = models.CharField(max_length=200, blank=True)
    supplier_contact = models.CharField(max_length=100, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['tenant', 'feed_type', 'batch_number']
    
    def __str__(self):
        return f"{self.feed_type.name} - {self.current_stock_kg} KG"
    
    @property
    def is_low_stock(self):
        return self.current_stock_kg <= self.minimum_stock_kg
    
    @property
    def needs_reorder(self):
        return self.current_stock_kg <= self.reorder_level_kg
    
    def update_average_cost(self):
        """Update average cost based on all purchases"""
        from decimal import Decimal
        
        purchases = self.purchases.all()
        if purchases.exists():
            total_quantity = sum(p.quantity_kg for p in purchases)
            total_value = sum(p.total_cost for p in purchases)
            if total_quantity > 0:
                self.average_cost_per_kg = total_value / total_quantity
                self.save(update_fields=['average_cost_per_kg'])


class FeedConsumption(models.Model):
    """Daily feed consumption records - tracks only physical feed usage"""
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='feed_consumption')
    batch = models.ForeignKey(FlockBatch, on_delete=models.CASCADE, related_name='feed_consumption')
    feed_type = models.ForeignKey(FeedType, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    
    FEEDING_TIME = [
        ('MORNING', 'Morning (6:00 - 10:00)'),
        ('AFTERNOON', 'Afternoon (12:00 - 15:00)'),
        ('EVENING', 'Evening (17:00 - 20:00)'),
    ]
    feeding_time = models.CharField(max_length=20, choices=FEEDING_TIME, default='MORNING')
    
    daily_record = models.ForeignKey(
        'DailyRecord', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='feed_consumptions'  # Note: plural to indicate multiple
    )
    
    # Feed tracking fields - ONLY these matter for consumption
    current_stock_kg = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    feed_given_kg = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    feed_remaining_kg = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Calculated fields
    feed_consumed_kg = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    feed_wasted_kg = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Birds count for per-bird calculation
    bird_count = models.IntegerField(default=0)
    feed_per_bird_grams = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['batch', 'date', 'feeding_time']),
        ]
    
    def save(self, *args, **kwargs):
        from decimal import Decimal
        
        # Calculate feed consumed = feed_given - feed_remaining
        self.feed_consumed_kg = self.feed_given_kg - self.feed_remaining_kg
        
        # Set feed_wasted_kg to 0 (you can customize this logic)
        self.feed_wasted_kg = Decimal('0')
        
        # Calculate feed per bird
        if self.bird_count > 0:
            bird_count_dec = Decimal(str(self.bird_count))
            self.feed_per_bird_grams = (self.feed_consumed_kg / bird_count_dec) * Decimal('1000')
        
        super().save(*args, **kwargs)
        
        # Update inventory - reduce stock by consumed amount
        inventory = FeedInventory.objects.filter(tenant=self.tenant, feed_type=self.feed_type).first()
        if inventory:
            current = Decimal(str(inventory.current_stock_kg))
            consumed = Decimal(str(self.feed_consumed_kg))
            inventory.current_stock_kg = current - consumed
            inventory.save(update_fields=['current_stock_kg'])


class FeedPurchase(models.Model):
    """Feed purchase records - ALL COST LOGIC IS HERE"""
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='feed_purchases')
    feed_type = models.ForeignKey(FeedType, on_delete=models.CASCADE)
    inventory = models.ForeignKey(FeedInventory, on_delete=models.CASCADE, related_name='purchases')
    
    purchase_date = models.DateField(default=timezone.now)
    invoice_number = models.CharField(max_length=100, blank=True)
    
    quantity_kg = models.DecimalField(max_digits=12, decimal_places=2)
    cost_per_kg = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    supplier_name = models.CharField(max_length=200)
    supplier_contact = models.CharField(max_length=100, blank=True)
    delivery_date = models.DateField(null=True, blank=True)
    delivery_notes = models.TextField(blank=True)
    
    payment_status = models.CharField(max_length=20, choices=[
        ('PAID', 'Paid'),
        ('PENDING', 'Pending'),
        ('PARTIAL', 'Partial'),
    ], default='PENDING')
    
    receipt = models.FileField(upload_to='feed/receipts/', null=True, blank=True)
    notes = models.TextField(blank=True)
    
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        from decimal import Decimal
        
        quantity = Decimal(str(self.quantity_kg))
        cost = Decimal(str(self.cost_per_kg))
        
        # Calculate total cost
        self.total_cost = quantity * cost
        
        super().save(*args, **kwargs)
        
        # Update inventory
        if self.inventory:
            current_stock = Decimal(str(self.inventory.current_stock_kg))
            avg_cost = Decimal(str(self.inventory.average_cost_per_kg))
            
            # Update current stock
            new_stock = current_stock + quantity
            self.inventory.current_stock_kg = new_stock
            
            # Update purchase info
            self.inventory.last_purchase_date = self.purchase_date
            self.inventory.last_purchase_quantity_kg = quantity
            self.inventory.last_purchase_cost = self.total_cost
            
            # Calculate new average cost
            total_value = (current_stock * avg_cost) + self.total_cost
            if new_stock > 0:
                new_avg_cost = total_value / new_stock
                self.inventory.average_cost_per_kg = new_avg_cost
            
            self.inventory.save()

class FeedConsumptionAlert(models.Model):
    """Alerts for feed consumption recommendations"""
    SEVERITY = [
        ('INFO', 'Information'),
        ('WARNING', 'Warning'),
        ('CRITICAL', 'Critical'),
    ]
    
    batch = models.ForeignKey(FlockBatch, on_delete=models.CASCADE, related_name='feed_alerts')
    alert_date = models.DateField(default=timezone.now)
    severity = models.CharField(max_length=20, choices=SEVERITY, default='INFO')
    title = models.CharField(max_length=200)
    message = models.TextField()
    recommended_feed_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    current_consumption_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-alert_date']
    
    def __str__(self):
        return f"{self.batch.batch_name} - {self.title}"



def generate_feed_alerts_for_batch(batch):
    """Generate feed consumption alerts based on feeding guide"""
    from decimal import Decimal
    from datetime import timedelta
    
    today = timezone.now().date()
    bird_count = batch.current_quantity
    age_weeks = batch.age_weeks
    
    if bird_count <= 0:
        return
    
    # Get feeding guide for current age
    try:
        guide = FeedingGuide.objects.filter(
            bird_type=batch.bird_type,
            week_start__lte=age_weeks,
            week_end__gte=age_weeks
        ).first()
    except FeedingGuide.DoesNotExist:
        return
    
    if not guide:
        return
    
    # Calculate recommended daily feed
    recommended_daily_kg = (float(guide.daily_feed_per_bird_grams) * bird_count) / 1000
    
    # Get actual consumption from last 7 days
    week_ago = today - timedelta(days=7)
    last_week_consumption = FeedConsumption.objects.filter(
        batch=batch,
        date__gte=week_ago,
        date__lte=today
    )
    
    consumption_count = last_week_consumption.count()
    if consumption_count > 0:
        actual_daily_avg = sum(float(c.total_daily_consumption) for c in last_week_consumption) / consumption_count
    else:
        actual_daily_avg = 0
    
    # Create daily recommendation alert (always show for awareness)
    FeedConsumptionAlert.objects.get_or_create(
        batch=batch,
        week_number=age_weeks,
        title=f'Week {age_weeks} Feed Recommendation',
        defaults={
            'severity': 'INFO',
            'alert_date': today,
            'title': f'Week {age_weeks} - Daily Feed Recommendation',
            'message': f'Based on your flock size of {bird_count} birds at week {age_weeks}, you should feed approximately {recommended_daily_kg:.1f} kg per day.',
            'recommended_feed_kg': recommended_daily_kg,
            'recommended_per_bird_grams': int(guide.daily_feed_per_bird_grams),
            'bird_count': bird_count,
            'week_number': age_weeks
        }
    )
    
    # Create alert if consumption is off by more than 15%
    if actual_daily_avg > 0:
        variance_percent = abs((actual_daily_avg - recommended_daily_kg) / recommended_daily_kg * 100)
        
        if variance_percent > 15:
            severity = 'CRITICAL' if variance_percent > 30 else 'WARNING'
            alert_type = 'Overfeeding' if actual_daily_avg > recommended_daily_kg else 'Underfeeding'
            
            FeedConsumptionAlert.objects.get_or_create(
                batch=batch,
                week_number=age_weeks,
                title=f'{alert_type} Alert - Week {age_weeks}',
                defaults={
                    'severity': severity,
                    'alert_date': today,
                    'title': f'{alert_type} Alert - Week {age_weeks}',
                    'message': f'Feed consumption is {variance_percent:.1f}% {alert_type.lower()} recommended amount.',
                    'recommended_feed_kg': recommended_daily_kg,
                    'current_consumption_kg': actual_daily_avg,
                    'recommended_per_bird_grams': int(guide.daily_feed_per_bird_grams),
                    'current_per_bird_grams': int((actual_daily_avg / bird_count) * 1000) if bird_count > 0 else 0,
                    'bird_count': bird_count,
                    'week_number': age_weeks
                }
            )