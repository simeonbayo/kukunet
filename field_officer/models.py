# field_officer/models.py
from django.db import models
from django.conf import settings

class FarmVisit(models.Model):
    """Record of farm visits by field officers"""
    VISIT_STATUS = [
        ('SCHEDULED', 'Scheduled'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('RESCHEDULED', 'Rescheduled'),
    ]
    
    field_officer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='farm_visits')
    farmer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='field_visits')
    farm = models.ForeignKey('farm.Farm', on_delete=models.CASCADE, null=True, blank=True)
    scheduled_date = models.DateTimeField()
    actual_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=VISIT_STATUS, default='SCHEDULED')
    purpose = models.TextField()
    findings = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.IntegerField(default=0)
    location_lat = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    location_lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-scheduled_date']
    
    def __str__(self):
        return f"{self.field_officer.full_name} visit to {self.farmer.full_name}"

class HealthAdvisory(models.Model):
    """Health advisories and alerts from field officers"""
    PRIORITY = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY, default='MEDIUM')
    disease_type = models.CharField(max_length=100, blank=True)
    symptoms = models.TextField(blank=True)
    prevention_measures = models.TextField(blank=True)
    treatment = models.TextField(blank=True)
    affected_districts = models.TextField(blank=True, help_text="Comma-separated districts")
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='advisories')
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-priority', '-created_at']
        verbose_name_plural = "Health Advisories"
    
    def __str__(self):
        return self.title

class TrainingSession(models.Model):
    """Training sessions conducted by field officers"""
    SESSION_TYPE = [
        ('WORKSHOP', 'Workshop'),
        ('SEMINAR', 'Seminar'),
        ('DEMONSTRATION', 'Demonstration'),
        ('ONE_ON_ONE', 'One-on-One Training'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    session_type = models.CharField(max_length=20, choices=SESSION_TYPE)
    field_officer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trainings')
    attendees = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='trainings_attended', blank=True)
    location = models.CharField(max_length=200)
    scheduled_date = models.DateTimeField()
    actual_date = models.DateTimeField(null=True, blank=True)
    duration_hours = models.IntegerField(default=1)
    materials_used = models.TextField(blank=True)
    feedback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-scheduled_date']
    
    def __str__(self):
        return self.title