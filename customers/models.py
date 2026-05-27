from django.db import models
from app.mixins import SoftDeleteModel
from app.validators import validate_angolan_nif, email_validator


class Customer(SoftDeleteModel):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, null=True, blank=True, related_name='customers')
    name = models.CharField(max_length=500, db_index=True)
    phone = models.CharField(max_length=20, blank=True)
    nif = models.CharField(max_length=20, blank=True, validators=[validate_angolan_nif], db_index=True)
    address = models.TextField(blank=True)
    email = models.EmailField(blank=True, validators=[email_validator], db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
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
        ]

    def __str__(self):
        return self.name

    def delete(self, using=None, keep_parents=False):
        from audit.signals import log_action
        log_action(self, 'DELETE')
        super().delete(using=using, keep_parents=keep_parents)
