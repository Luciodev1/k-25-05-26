from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from customers.models import Customer
from app.mixins import SoftDeleteModel


class CustomerAccess(SoftDeleteModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_access')
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='portal_access')
    is_active = models.BooleanField(default=True, verbose_name='Acesso Ativo')
    last_login = models.DateTimeField(null=True, blank=True, verbose_name='Último Acesso')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Acesso do Cliente'
        verbose_name_plural = 'Acessos dos Clientes'

    def __str__(self):
        return f'{self.customer.name} - {self.user.username}'


class PortalSessionLog(models.Model):
    access = models.ForeignKey(
        CustomerAccess, on_delete=models.CASCADE,
        related_name='session_logs',
    )
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    action = models.CharField(
        max_length=20, choices=[
            ('login', 'Login'),
            ('logout', 'Logout'),
            ('password_change', 'Alteração de Password'),
        ],
        db_index=True,
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        verbose_name = 'Registo de Sessão'
        verbose_name_plural = 'Registos de Sessão'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['access', 'created_at']),
            models.Index(fields=['access', 'action']),
        ]

    def __str__(self):
        return f'{self.access} - {self.action} ({self.created_at:%d/%m/%Y %H:%M})'
