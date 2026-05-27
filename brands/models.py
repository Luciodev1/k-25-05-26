from django.db import models
from app.mixins import SoftDeleteModel


class Brand(SoftDeleteModel):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, null=True, blank=True, related_name='brands')
    name = models.CharField(max_length=100, db_index=True)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Brand'
        verbose_name_plural = 'Brands'
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
        ]

    def __str__(self):
        return self.name

    def delete(self, using=None, keep_parents=False):
        from audit.signals import log_action
        log_action(self, 'DELETE')
        super().delete(using=using, keep_parents=keep_parents)
    
    
