from django.db import models
from django.utils import timezone

class Farm(models.Model):
    FARM_TYPES = [
        ('LAYERS', 'Layers'),
        ('BROILERS', 'Broilers'),
        ('BREEDERS', 'Breeders'),
        ('MIXED', 'Mixed'),
    ]
    
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)
    farm_name = models.CharField(max_length=100)
    farm_type = models.CharField(max_length=20, choices=FARM_TYPES)
    district = models.CharField(max_length=100)
    village = models.CharField(max_length=100)
    size_acres = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.farm_name

class House(models.Model):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='houses')
    name = models.CharField(max_length=100)
    capacity = models.IntegerField()
    current_population = models.IntegerField(default=0)
    house_type = models.CharField(max_length=50, choices=[
        ('OPEN', 'Open House'),
        ('CLOSED', 'Closed House'),
        ('BATTERY', 'Battery Cages')
    ])
    
    def __str__(self):
        return f"{self.farm.farm_name} - {self.name}"

class FlockBatch(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('CULLED', 'Culled'),
        ('DEPLETED', 'Depleted'),
    ]
    
    BIRD_TYPES = [
        ('LAYERS', 'Layers'),
        ('BROILERS', 'Broilers'),
        ('DAY_OLD', 'Day Old Chicks'),
        ('GROWERS', 'Growers'),
        ('BREEDERS', 'Breeders'),
    ]
    
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE)
    house = models.ForeignKey(House, on_delete=models.CASCADE)
    batch_name = models.CharField(max_length=100)
    bird_type = models.CharField(max_length=20, choices=BIRD_TYPES)
    breed = models.CharField(max_length=100)
    quantity = models.IntegerField()
    start_date = models.DateField()
    expected_end_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    @property
    def age_days(self):
        return (timezone.now().date() - self.start_date).days
    
    @property
    def mortality_rate(self):
        total_mortality = self.daily_records.aggregate(
            total=models.Sum('mortality')
        )['total'] or 0
        return (total_mortality / self.quantity) * 100 if self.quantity > 0 else 0
    
    def __str__(self):
        return self.batch_name

class DailyRecord(models.Model):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)
    batch = models.ForeignKey(FlockBatch, on_delete=models.CASCADE, related_name='daily_records')
    date = models.DateField(default=timezone.now)
    mortality = models.IntegerField(default=0)
    feed_used_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    water_used_liters = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    eggs_collected = models.IntegerField(default=0)  # For layers
    avg_weight_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['batch', 'date']
        ordering = ['-date']

class VaccinationRecord(models.Model):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)
    batch = models.ForeignKey(FlockBatch, on_delete=models.CASCADE, related_name='vaccinations')
    vaccine_name = models.CharField(max_length=100)
    scheduled_date = models.DateField()
    administered_date = models.DateField(null=True, blank=True)
    administered_by = models.CharField(max_length=100, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=[
        ('SCHEDULED', 'Scheduled'),
        ('COMPLETED', 'Completed'),
        ('MISSED', 'Missed')
    ], default='SCHEDULED')

class Expense(models.Model):
    EXPENSE_CATEGORIES = [
        ('FEED', 'Feed'),
        ('VACCINES', 'Vaccines'),
        ('MEDICATION', 'Medication'),
        ('LABOR', 'Labor'),
        ('UTILITIES', 'Utilities'),
        ('MAINTENANCE', 'Maintenance'),
        ('TRANSPORT', 'Transport'),
        ('OTHER', 'Other'),
    ]
    
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='expenses')
    batch = models.ForeignKey(FlockBatch, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.CharField(max_length=20, choices=EXPENSE_CATEGORIES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField()
    expense_date = models.DateField(default=timezone.now)
    receipt = models.FileField(upload_to='receipts/', null=True, blank=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)