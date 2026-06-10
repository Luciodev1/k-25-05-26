from django.conf import settings
from django.db import models
from django.utils import timezone


class ExportJob(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('processing', 'Processando'),
        ('completed', 'Concluído'),
        ('failed', 'Falhou'),
    ]

    REPORT_TYPE_CHOICES = [
        ('outflows_by_customer', 'Saídas por Cliente'),
        ('deliveries', 'Entregas'),
        ('customer_account', 'Extrato de Clientes'),
        ('supplier_account', 'Extrato de Fornecedores'),
        ('balances', 'Saldos'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Utilizador')
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, verbose_name='Empresa')
    task_id = models.CharField(max_length=255, blank=True, db_index=True, verbose_name='ID da Task')
    report_type = models.CharField(max_length=100, choices=REPORT_TYPE_CHOICES, verbose_name='Tipo de Relatório')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Estado')
    filters = models.JSONField(default=dict, verbose_name='Filtros')
    export_format = models.CharField(max_length=10, default='excel', verbose_name='Formato')
    file_path = models.CharField(max_length=500, blank=True, verbose_name='Caminho do Ficheiro')
    error_message = models.TextField(blank=True, verbose_name='Mensagem de Erro')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Concluído em')

    class Meta:
        verbose_name = 'Job de Exportação'
        verbose_name_plural = 'Jobs de Exportação'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_report_type_display()} - {self.get_status_display()} ({self.created_at})'

    def mark_processing(self):
        self.status = 'processing'
        self.save(update_fields=['status'])

    def mark_completed(self, file_path: str):
        self.status = 'completed'
        self.file_path = file_path
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'file_path', 'completed_at'])

    def mark_failed(self, error_message: str):
        self.status = 'failed'
        self.error_message = error_message
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'error_message', 'completed_at'])
