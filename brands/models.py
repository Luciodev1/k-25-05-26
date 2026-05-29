from django.db import models
from app.mixins import SoftDeleteModel
from audit.signals import log_action


class Brand(SoftDeleteModel):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='brands', null=True, blank=True)
    name = models.CharField(max_length=100, db_index=True, verbose_name='Nome')
    description = models.TextField(null=True, blank=True, verbose_name='Descrição')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Marca'
        verbose_name_plural = 'Marcas'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'name'],
                condition=models.Q(is_deleted=False),
                name='brand_name_unique_per_tenant',
            ),
        ]
        indexes = [
            models.Index(fields=['tenant', 'name']),
            models.Index(fields=['tenant', 'is_deleted']),
        ]

    def __str__(self):
        return self.name

    def delete(self, using=None, keep_parents=False):
        log_action(self, 'DELETE')
        super().delete(using=using, keep_parents=keep_parents)
    
    
