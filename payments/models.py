from django.db import models, transaction
from django.core.validators import MinValueValidator
from django.db.models import Q
from customers.models import Customer
from suppliers.models import Supplier
from app.mixins import SoftDeleteModel
from app.validators import validate_payment_date
from audit.signals import log_action


class Payment(SoftDeleteModel):
    TYPE_CHOICES = [
        ('RECEIPT', 'Recebimento (Cliente)'),
        ('PAYMENT', 'Pagamento (Fornecedor)'),
    ]

    METHOD_CHOICES = [
        ('CASH', 'Dinheiro'),
        ('TRANSFER', 'Transferência Bancária'),
        ('TPA', 'TPA'),
        ('DEPOSIT', 'Depósito'),
    ]

    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, verbose_name='Tipo')
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, null=True, blank=True, related_name='payments', verbose_name='Cliente')
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, null=True, blank=True, related_name='payments', verbose_name='Fornecedor')
    amount = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='Valor')
    payment_method = models.CharField(max_length=20, choices=METHOD_CHOICES, verbose_name='Método de Pagamento')
    date = models.DateField(verbose_name='Data', db_index=True, validators=[validate_payment_date])
    description = models.TextField(null=True, blank=True, verbose_name='Descrição')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Pagamento'
        verbose_name_plural = 'Pagamentos'
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['tenant', 'is_deleted']),
            models.Index(fields=['tenant', 'date']),
            models.Index(fields=['tenant', 'type']),
            models.Index(fields=['tenant', 'customer']),
            models.Index(fields=['tenant', 'supplier']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    (Q(type='RECEIPT') & Q(customer__isnull=False) & Q(supplier__isnull=True)) |
                    (Q(type='PAYMENT') & Q(supplier__isnull=False) & Q(customer__isnull=True))
                ),
                name='payment_entity_required',
            ),
        ]

    def __str__(self):
        entity = self.customer if self.type == 'RECEIPT' else self.supplier
        return f'{self.get_type_display()} - {entity} ({self.amount})'

    def delete(self, using=None, keep_parents=False):
        """Soft delete com limpeza de contas."""
        with transaction.atomic():
            from accounts.models import CustomerAccountEntry, SupplierAccountEntry
            if self.type == 'RECEIPT':
                CustomerAccountEntry.objects.filter(payment=self, tenant=self.tenant).delete()
            else:
                SupplierAccountEntry.objects.filter(payment=self, tenant=self.tenant).delete()
            log_action(self, 'DELETE')
            super().delete(using=using, keep_parents=keep_parents)
