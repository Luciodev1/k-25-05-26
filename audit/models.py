from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Criacao'),
        ('UPDATE', 'Alteracao'),
        ('DELETE', 'Eliminacao'),
    ]

    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
    )
    action = models.CharField(max_length=10, choices=ACTION_CHOICES, db_index=True)
    model_name = models.CharField(max_length=100, db_index=True)
    object_id = models.CharField(max_length=50)
    object_repr = models.CharField(max_length=200)
    changes = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Registo de Auditoria'
        verbose_name_plural = 'Registos de Auditoria'
        indexes = [
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['tenant', 'timestamp']),
            models.Index(fields=['tenant', 'action']),
        ]

    def __str__(self):
        return f'{self.get_action_display()} - {self.model_name} #{self.object_id} por {self.user or "sistema"}'
