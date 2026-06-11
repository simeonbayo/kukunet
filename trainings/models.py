# trainings/models.py
from django.db import models
from django.utils import timezone
from accounts.models import User
from tenants.models import Tenant

class Training(models.Model):
    """Farmer training program model"""
    
    STATUS_CHOICES = [
        ('UPCOMING', 'Upcoming'),
        ('ONGOING', 'Ongoing'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    TRAINING_TYPES = [
        ('POULTRY_HEALTH', 'Poultry Health Management'),
        ('FEED_FORMULATION', 'Feed Formulation'),
        ('RECORD_KEEPING', 'Record Keeping'),
        ('BREEDING', 'Breeding Techniques'),
        ('MARKETING', 'Marketing & Sales'),
        ('BIO_SECURITY', 'Bio-security'),
        ('WASTE_MANAGEMENT', 'Waste Management'),
        ('BUSINESS_SKILLS', 'Business Skills'),
        ('OTHER', 'Other'),
    ]
    
    # Organization
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='trainings')
    
    # Basic Info
    title = models.CharField(max_length=200)
    training_type = models.CharField(max_length=30, choices=TRAINING_TYPES, default='OTHER')
    description = models.TextField(blank=True)
    topics_covered = models.TextField(blank=True, help_text="List of topics to be covered")
    
    # Schedule
    start_date = models.DateField()
    end_date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    
    # Location
    venue = models.CharField(max_length=255)
    district = models.CharField(max_length=100, blank=True)
    village = models.CharField(max_length=100, blank=True)
    gps_coordinates = models.CharField(max_length=100, blank=True)
    
    # Trainer Info
    trainer_name = models.CharField(max_length=200)
    trainer_contact = models.CharField(max_length=20, blank=True)
    trainer_email = models.EmailField(blank=True)
    trainer_organization = models.CharField(max_length=200, blank=True)
    
    # Participants - FIXED: Added unique related_name
    expected_participants = models.IntegerField(default=0)
    actual_participants = models.IntegerField(default=0)
    farmers = models.ManyToManyField(
        User, 
        related_name='training_programs',  # Changed from 'trainings' to 'training_programs'
        blank=True, 
        limit_choices_to={'role': 'FARMER'}
    )
    
    # Resources
    materials_provided = models.TextField(blank=True, help_text="List of materials/training materials provided")
    budget = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    actual_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UPCOMING')
    notes = models.TextField(blank=True)
    
    # Feedback
    feedback_summary = models.TextField(blank=True)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    
    # Metadata
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_training_programs'  # Changed to unique related_name
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['start_date']),
            models.Index(fields=['tenant', 'status']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.start_date} - {self.end_date})"
    
    @property
    def duration_days(self):
        return (self.end_date - self.start_date).days + 1
    
    @property
    def is_upcoming(self):
        return self.start_date > timezone.now().date()
    
    @property
    def is_ongoing(self):
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date
    
    @property
    def is_completed(self):
        return self.end_date < timezone.now().date()
    
    def save(self, *args, **kwargs):
        # Auto-update status based on dates
        if self.is_upcoming and self.status == 'UPCOMING':
            pass
        elif self.is_ongoing and self.status != 'CANCELLED':
            self.status = 'ONGOING'
        elif self.is_completed and self.status != 'CANCELLED':
            self.status = 'COMPLETED'
        super().save(*args, **kwargs)


class TrainingAttendance(models.Model):
    """Track attendance for each training session"""
    
    ATTENDANCE_STATUS = [
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('LATE', 'Late'),
        ('EXCUSED', 'Excused'),
    ]
    
    training = models.ForeignKey(Training, on_delete=models.CASCADE, related_name='attendance_records')
    farmer = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='training_attendance_records'  # Changed to unique related_name
    )
    attendance_status = models.CharField(max_length=20, choices=ATTENDANCE_STATUS, default='PRESENT')
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['training', 'farmer']
        ordering = ['training', '-check_in_time']
    
    def __str__(self):
        return f"{self.farmer.full_name} - {self.training.title} - {self.attendance_status}"


class TrainingEvaluation(models.Model):
    """Post-training evaluation and feedback"""
    
    RATING_CHOICES = [(i, i) for i in range(1, 6)]
    
    training = models.ForeignKey(Training, on_delete=models.CASCADE, related_name='evaluations')
    farmer = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='training_evaluations'  # Changed to unique related_name
    )
    
    # Ratings
    content_rating = models.IntegerField(choices=RATING_CHOICES, help_text="Rating for training content")
    trainer_rating = models.IntegerField(choices=RATING_CHOICES, help_text="Rating for trainer effectiveness")
    materials_rating = models.IntegerField(choices=RATING_CHOICES, help_text="Rating for training materials")
    venue_rating = models.IntegerField(choices=RATING_CHOICES, help_text="Rating for venue/facilities")
    overall_rating = models.IntegerField(choices=RATING_CHOICES, help_text="Overall satisfaction rating")
    
    # Feedback
    what_was_good = models.TextField(blank=True)
    what_needs_improvement = models.TextField(blank=True)
    suggestions = models.TextField(blank=True)
    would_recommend = models.BooleanField(default=True)
    
    # Follow-up
    interested_in_follow_up = models.BooleanField(default=False)
    follow_up_topic = models.CharField(max_length=200, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['training', 'farmer']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Evaluation for {self.training.title} by {self.farmer.full_name}"