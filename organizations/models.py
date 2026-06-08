# organizations/models.py
from django.db import models
from django.conf import settings

class OrganizationProfile(models.Model):
    """Extended profile for organization users"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organization_profile')
    logo = models.ImageField(upload_to='organizations/logos/', null=True, blank=True)
    cover_image = models.ImageField(upload_to='organizations/covers/', null=True, blank=True)
    description = models.TextField(blank=True)
    mission = models.TextField(blank=True)
    vision = models.TextField(blank=True)
    established_year = models.IntegerField(null=True, blank=True)
    employee_count = models.IntegerField(default=0)
    branches = models.TextField(blank=True, help_text="Comma-separated branch locations")
    social_media = models.JSONField(default=dict, help_text="Social media links")
    is_verified = models.BooleanField(default=False)
    verification_documents = models.FileField(upload_to='organizations/documents/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Profile of {self.user.organization_name}"

class OrganizationMember(models.Model):
    """Members of an organization (employees, agents)"""
    ROLE_CHOICES = [
        ('ADMIN', 'Organization Admin'),
        ('MANAGER', 'Manager'),
        ('STAFF', 'Staff Member'),
        ('AGENT', 'Field Agent'),
        ('VOLUNTEER', 'Volunteer'),
    ]
    
    organization = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organizations')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='STAFF')
    department = models.CharField(max_length=100, blank=True)
    joined_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['organization', 'user']
    
    def __str__(self):
        return f"{self.user.full_name} - {self.organization.organization_name}"

class OrganizationProject(models.Model):
    """Projects run by organizations"""
    STATUS_CHOICES = [
        ('PLANNING', 'Planning'),
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('SUSPENDED', 'Suspended'),
    ]
    
    organization = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='projects')
    title = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    budget = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLANNING')
    beneficiaries = models.IntegerField(default=0)
    location = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title

class Partnership(models.Model):
    """Partnerships between organizations and other entities"""
    PARTNER_TYPE = [
        ('ORGANIZATION', 'Organization'),
        ('GOVERNMENT', 'Government Agency'),
        ('NGO', 'Non-Profit'),
        ('PRIVATE', 'Private Company'),
    ]
    
    organization = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='partnerships')
    partner_name = models.CharField(max_length=200)
    partner_type = models.CharField(max_length=20, choices=PARTNER_TYPE)
    agreement_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.organization.organization_name} - {self.partner_name}"
    

# organizations/models.py - Add this model
class OrganizationFarmer(models.Model):
    """Farmers registered under an organization"""
    
    FARM_TYPES = [
        ('LAYERS', 'Layers'),
        ('BROILERS', 'Broilers'),
        ('BREEDERS', 'Breeders'),
        ('MIXED', 'Mixed'),
    ]
    
    organization = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='registered_farmers'
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='organization_farmer'
    )
    farm = models.OneToOneField(
        'farm.Farm', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='organization_farmer'
    )
    
    # Basic Information
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    
    # Location
    village = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    gps_coordinates = models.CharField(max_length=100, blank=True, help_text="Latitude,Longitude")
    
    # Farm Details
    farm_type = models.CharField(max_length=20, choices=FARM_TYPES, default='LAYERS')
    farm_size_acres = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    registration_date = models.DateField(auto_now_add=True)
    
    # Additional Info
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_farmers'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['organization', 'phone']
    
    def __str__(self):
        return f"{self.name} - {self.organization.organization_name}"