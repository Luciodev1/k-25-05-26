from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password
from app.mixins import SoftDeleteModel
import uuid


class Tenant(SoftDeleteModel):
    """Model representing a tenant (organization/company)"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Tenant configuration
    currency = models.CharField(max_length=3, default='AOA')
    timezone = models.CharField(max_length=50, default='Africa/Luanda')
    language = models.CharField(max_length=5, default='pt-pt')
    
    # Tenant settings
    allow_self_registration = models.BooleanField(default=False)
    require_email_verification = models.BooleanField(default=True)
    max_users = models.IntegerField(default=10)
    storage_limit = models.IntegerField(default=1024)  # MB
    
    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def get_tenant_users(self):
        """Get all active users associated with this tenant"""
        return User.objects.filter(
            tenantuser__tenant=self,
            is_active=True,
        ).distinct()
    
    def get_active_users_count(self):
        """Get count of active users for this tenant"""
        return self.get_tenant_users().count()
    
    def can_add_user(self):
        """Check if tenant can add more users"""
        return self.get_active_users_count() < self.max_users


class TenantUser(SoftDeleteModel):
    """Model for many-to-many relationship between User and Tenant with role"""
    
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('manager', 'Manager'),
        ('operator', 'Operator'),
        ('viewer', 'Viewer'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='operator')
    is_primary = models.BooleanField(default=False)  # User's primary tenant
    joined_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Utilizador da Empresa'
        verbose_name_plural = 'Utilizadores da Empresa'
        unique_together = ['user', 'tenant']
        ordering = ['-joined_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.tenant.name} ({self.role})"
    
    def has_permission(self, permission):
        """Check if user has specific permission based on role"""
        role_permissions = {
            'admin': ['view', 'add', 'change', 'delete', 'manage'],
            'manager': ['view', 'add', 'change', 'delete'],
            'operator': ['view', 'add', 'change'],
            'viewer': ['view'],
        }
        return permission in role_permissions.get(self.role, [])


class TenantSettings(SoftDeleteModel):
    """Model for tenant-specific settings"""
    
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE)
    
    # Notification settings
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    push_notifications = models.BooleanField(default=True)
    
    # Security settings
    password_expiry_days = models.IntegerField(default=90)
    min_password_length = models.IntegerField(default=8)
    require_mfa = models.BooleanField(default=False)
    
    # Workflow settings
    require_approval_for_sales = models.BooleanField(default=False)
    require_approval_for_purchases = models.BooleanField(default=False)
    auto_approve_below_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    
    # Reporting settings
    auto_generate_reports = models.BooleanField(default=False)
    report_frequency = models.CharField(
        max_length=20, 
        choices=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
        ],
        default='weekly'
    )
    
    # Integration settings
    enable_api_access = models.BooleanField(default=False)
    api_key = models.CharField(max_length=255, blank=True, help_text='Guardado como hash — não recuperável.')

    def set_api_key(self, raw_key):
        self.api_key = make_password(raw_key)

    def check_api_key(self, raw_key):
        if not self.api_key:
            return False
        return check_password(raw_key, self.api_key)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Configurações da Empresa'
        verbose_name_plural = 'Configurações da Empresa'
    
    def __str__(self):
        return f"Settings for {self.tenant.name}"