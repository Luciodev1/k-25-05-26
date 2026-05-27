from django.db import models
from app.mixins import SoftDeleteModel


class Driver(SoftDeleteModel):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, null=True, blank=True, related_name='drivers')
    name = models.CharField(max_length=200, verbose_name='Nome', db_index=True)
    phone = models.CharField(max_length=20, verbose_name='Telefone')
    truck_plate = models.CharField(max_length=50, verbose_name='Matrícula do Caminhão', db_index=True)
    cistern_plate = models.CharField(max_length=50, verbose_name='Matrícula da Cisterna', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Motorista'
        verbose_name_plural = 'Motoristas'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['truck_plate'],
                condition=models.Q(is_deleted=False),
                name='driver_truck_plate_unique',
            ),
            models.UniqueConstraint(
                fields=['cistern_plate'],
                condition=models.Q(is_deleted=False),
                name='driver_cistern_plate_unique',
            ),
        ]

    def __str__(self):
        return f'{self.name} ({self.truck_plate})'

    def delete(self, using=None, keep_parents=False):
        from audit.signals import log_action
        log_action(self, 'DELETE')
        super().delete(using=using, keep_parents=keep_parents)
