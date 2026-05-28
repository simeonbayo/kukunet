# accounts/models.py - Complete working version
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator, MinLengthValidator

class UserManager(BaseUserManager):
    def create_user(self, phone_number, pin=None, full_name='', **extra_fields):
        if not phone_number:
            raise ValueError('Phone number is required')
        
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
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        # If no PIN provided, use a default (you should change this)
        if pin is None:
            pin = '1234'
            print("Warning: Using default PIN '1234' for superuser. Change it immediately!")
        
        return self.create_user(phone_number, pin, full_name, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('FARMER', 'Farmer'),
        ('CUSTOMER', 'Customer'),
        ('SUPPLIER', 'Supplier'),
        ('TRAINER', 'Trainer'),
        ('ADMIN', 'Admin'),
        ('SUPER_ADMIN', 'Super Admin'),
    ]
    
    phone_number = models.CharField(
        max_length=15,
        unique=True,
        validators=[RegexValidator(r'^[0-9]{10,15}$', 'Enter a valid phone number')]
    )
    full_name = models.CharField(max_length=200, blank=True)
    pin_hash = models.CharField(max_length=128, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='FARMER')
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['full_name']
    
    objects = UserManager()
    
    def set_pin(self, pin):
        """Set the PIN (hashed)"""
        self.set_password(str(pin))
        self.pin_hash = self.password
    
    def verify_pin(self, pin):
        """Verify the PIN"""
        return self.check_password(str(pin))
    
    def __str__(self):
        return f"{self.full_name} ({self.phone_number})"
    
    class Meta:
        ordering = ['-created_at']

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_photo = models.ImageField(upload_to='profiles/', null=True, blank=True)
    district = models.CharField(max_length=100, blank=True)
    village = models.CharField(max_length=100, blank=True)
    language = models.CharField(max_length=10, default='en')
    last_login_device = models.CharField(max_length=200, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Profile for {self.user.full_name}"