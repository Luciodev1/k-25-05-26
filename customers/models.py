from django.db import models
from app.mixins import SoftDeleteModel
from app.validators import validate_angolan_nif, email_validator
from audit.signals import log_action


class Customer(SoftDeleteModel):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='customers')
    name = models.CharField(max_length=500, db_index=True, verbose_name='Nome')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Telefone')
    nif = models.CharField(max_length=20, blank=True, validators=[validate_angolan_nif], db_index=True, verbose_name='NIF')
    address = models.TextField(blank=True, verbose_name='Endereço')
    email = models.EmailField(blank=True, validators=[email_validator], db_index=True, verbose_name='Email')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'nif'],
                condition=models.Q(is_deleted=False) & models.Q(nif__isnull=False) & ~models.Q(nif=''),
                name='customer_nif_unique_per_tenant',
            ),
        ]
        indexes = [
            models.Index(fields=['tenant', 'name']),
            models.Index(fields=['tenant', 'nif']),
            models.Index(fields=['tenant', 'email']),
            models.Index(fields=['tenant', 'is_deleted']),
            models.Index(fields=['tenant', 'created_at']),
        ]

    def __str__(self):
        return self.name

    def delete(self, using=None, keep_parents=False):
        log_action(self, 'DELETE')
        super().delete(using=using, keep_parents=keep_parents)
