# accounts/models.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator
from django.utils import timezone

class UserManager(BaseUserManager):
    def create_user(self, phone_number, pin=None, full_name='', **extra_fields):
        if not phone_number:
            raise ValueError('Phone number is required')
        
        phone_number = self.normalize_phone_number(phone_number)
        
        user = self.model(
            phone_number=phone_number,
            full_name=full_name,
            **extra_fields
        )
        
        if pin:
            user.set_pin(pin)
        else:
            user.set_unusable_password()
        
        user.save(using=self._db)
        return user
    
    def create_superuser(self, phone_number, pin=None, full_name='', **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'SUPER_ADMIN')
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        if pin is None:
            pin = '1234'
            print("Warning: Using default PIN '1234' for superuser!")
        
        return self.create_user(phone_number, pin, full_name, **extra_fields)
    
    def normalize_phone_number(self, phone_number):
        phone_number = ''.join(filter(str.isdigit, phone_number))
        
        if len(phone_number) == 9:
            phone_number = '256' + phone_number
        elif len(phone_number) == 10 and phone_number.startswith('0'):
            phone_number = '256' + phone_number[1:]
        
        return phone_number

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('FARMER', 'Farmer'),
        ('CUSTOMER', 'Customer'),
        ('SUPPLIER', 'Supplier'),
        ('TRAINER', 'Trainer'),
        ('FIELD_OFFICER', 'Field Officer (Vet/Extension Worker)'),
        ('ORGANIZATION', 'Organization'),
        ('ADMIN', 'Admin'),
        ('SUPER_ADMIN', 'Super Admin'),
    ]
    
    # Organization specific fields
    ORGANIZATION_TYPES = [
        ('COOPERATIVE', 'Cooperative'),
        ('AGRIBUSINESS', 'Agribusiness'),
        ('NGO', 'Non-Profit Organization'),
        ('GOVERNMENT', 'Government Agency'),
        ('RESEARCH', 'Research Institution'),
        ('OTHER', 'Other'),
    ]
    
    phone_number = models.CharField(
        max_length=15,
        unique=True,
        validators=[RegexValidator(r'^[0-9]{10,15}$', 'Enter a valid phone number')],
        db_index=True
    )
    full_name = models.CharField(max_length=200, blank=True)
    pin_hash = models.CharField(max_length=128, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='FARMER')
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.SET_NULL, null=True, blank=True, db_index=True)

    # Organization join code (for farmers to join an existing organization)
    organization_join_code = models.CharField(max_length=20, blank=True, help_text="Tenant code to join an organization")
    
    # Field Officer specific fields
    specialization = models.CharField(max_length=100, blank=True, help_text="e.g., Poultry Vet, Livestock Extension")
    license_number = models.CharField(max_length=100, blank=True, help_text="Professional license number")
    years_experience = models.IntegerField(default=0)
    assigned_districts = models.TextField(blank=True, help_text="Comma-separated list of districts")
    
    # Organization specific fields
    organization_name = models.CharField(max_length=200, blank=True)
    organization_type = models.CharField(max_length=20, choices=ORGANIZATION_TYPES, blank=True)
    registration_number = models.CharField(max_length=100, blank=True)
    tax_id = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    
    # Common fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['full_name']
    
    objects = UserManager()
    
    def set_pin(self, pin):
        self.set_password(str(pin))
        self.pin_hash = self.password
    
    def verify_pin(self, pin):
        if self.locked_until and self.locked_until > timezone.now():
            return False
        
        is_valid = self.check_password(str(pin))
        
        if is_valid:
            self.login_attempts = 0
            self.locked_until = None
            self.save(update_fields=['login_attempts', 'locked_until'])
        else:
            self.login_attempts += 1
            if self.login_attempts >= 5:
                self.locked_until = timezone.now() + timezone.timedelta(minutes=15)
            self.save(update_fields=['login_attempts', 'locked_until'])
        
        return is_valid
    
    @property
    def is_field_officer(self):
        return self.role == 'FIELD_OFFICER'
    
    @property
    def is_organization(self):
        return self.role == 'ORGANIZATION'
    
    def __str__(self):
        if self.role == 'ORGANIZATION' and self.organization_name:
            return f"{self.organization_name} ({self.phone_number})"
        return f"{self.full_name} ({self.phone_number})"
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['role']),
            models.Index(fields=['tenant']),
        ]

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_photo = models.ImageField(upload_to='profiles/%Y/%m/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    district = models.CharField(max_length=100, blank=True)
    village = models.CharField(max_length=100, blank=True)
    language = models.CharField(max_length=10, choices=[
        ('en', 'English'),
        ('sw', 'Swahili'),
        ('lg', 'Luganda'),
    ], default='en')
    currency = models.CharField(max_length=3, default='UGX')
    timezone = models.CharField(max_length=50, default='Africa/Kampala')
    notification_preferences = models.JSONField(default=dict)
    last_login_device = models.CharField(max_length=200, blank=True)
    last_login_user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Profile of {self.user.full_name}"