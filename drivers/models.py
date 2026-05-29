from django.db import models
from app.mixins import SoftDeleteModel
from audit.signals import log_action


class Driver(SoftDeleteModel):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='drivers', null=True, blank=True)
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
        indexes = [
            models.Index(fields=['tenant', 'is_deleted']),
            models.Index(fields=['tenant', 'name']),
            models.Index(fields=['tenant', 'truck_plate']),
            models.Index(fields=['tenant', 'cistern_plate']),
            models.Index(fields=['tenant', 'created_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'truck_plate'],
                condition=models.Q(is_deleted=False),
                name='driver_truck_plate_unique',
            ),
            models.UniqueConstraint(
                fields=['tenant', 'cistern_plate'],
                condition=models.Q(is_deleted=False),
                name='driver_cistern_plate_unique',
            ),
        ]

    def __str__(self):
        return f'{self.name} ({self.truck_plate})'

    def delete(self, using=None, keep_parents=False):
        log_action(self, 'DELETE')
        super().delete(using=using, keep_parents=keep_parents)
