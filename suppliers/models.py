from django.db import models
from app.mixins import SoftDeleteModel
from app.validators import validate_angolan_nif, email_validator
from audit.signals import log_action


class Supplier(SoftDeleteModel):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='suppliers')
    name = models.CharField(max_length=500, db_index=True, verbose_name='Nome')
    description = models.TextField(null=True, blank=True, verbose_name='Descrição')
    nif = models.CharField(max_length=20, blank=True, validators=[validate_angolan_nif], db_index=True, verbose_name='NIF')
    email = models.EmailField(blank=True, validators=[email_validator], db_index=True, verbose_name='Email')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Fornecedor'
        verbose_name_plural = 'Fornecedores'
        ordering = ['name']
        indexes = [
            models.Index(fields=['tenant', 'name']),
            models.Index(fields=['tenant', 'is_deleted']),
            models.Index(fields=['tenant', 'email']),
            models.Index(fields=['tenant', 'nif']),
            models.Index(fields=['tenant', 'created_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'nif'],
                condition=models.Q(is_deleted=False) & models.Q(nif__isnull=False) & ~models.Q(nif=''),
                name='supplier_tenant_nif_unique',
            ),
        ]

    def __str__(self):
        return self.name

    def delete(self, using=None, keep_parents=False):
        log_action(self, 'DELETE')
        super().delete(using=using, keep_parents=keep_parents)
