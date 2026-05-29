from django.db import models
from django.db.models import Q

from customers.models import Customer
from suppliers.models import Supplier
from outflows.models import Outflow
from inflows.models import Inflow


class BaseAccountEntry(models.Model):
    date = models.DateTimeField(auto_now_add=True, db_index=True)
    description = models.CharField(max_length=500)
    debit = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    class Meta:
        abstract = True


class CustomerAccountEntry(BaseAccountEntry):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='customer_account_entries', null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='account_entries', verbose_name='Cliente')
    outflow = models.ForeignKey(Outflow, on_delete=models.SET_NULL, null=True, blank=True, related_name='account_entries', verbose_name='Saída')
    payment = models.ForeignKey('payments.Payment', on_delete=models.SET_NULL, null=True, blank=True, related_name='customer_account_entries', verbose_name='Pagamento')

    class Meta:
        verbose_name = 'Lançamento de Cliente'
        verbose_name_plural = 'Lançamentos de Clientes'
        ordering = ['-date']
        indexes = [
            models.Index(fields=['customer', 'date']),
            models.Index(fields=['customer', 'outflow']),
            models.Index(fields=['tenant', 'customer']),
            models.Index(fields=['tenant', 'date']),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(debit__gte=0), name='customer_entry_debit_non_negative'),
            models.CheckConstraint(condition=Q(credit__gte=0), name='customer_entry_credit_non_negative'),
            models.CheckConstraint(
                condition=(Q(debit__gt=0) & Q(credit=0)) | (Q(credit__gt=0) & Q(debit=0)),
                name='customer_entry_debit_credit_exclusive',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.customer.name} - {self.description}'


class SupplierAccountEntry(BaseAccountEntry):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='supplier_account_entries', null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='account_entries', verbose_name='Fornecedor')
    inflow = models.ForeignKey(Inflow, on_delete=models.SET_NULL, null=True, blank=True, related_name='account_entries', verbose_name='Entrada')
    payment = models.ForeignKey('payments.Payment', on_delete=models.SET_NULL, null=True, blank=True, related_name='supplier_account_entries', verbose_name='Pagamento')

    class Meta:
        verbose_name = 'Lançamento de Fornecedor'
        verbose_name_plural = 'Lançamentos de Fornecedores'
        ordering = ['-date']
        indexes = [
            models.Index(fields=['supplier', 'date']),
            models.Index(fields=['supplier', 'inflow']),
            models.Index(fields=['tenant', 'supplier']),
            models.Index(fields=['tenant', 'date']),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(debit__gte=0), name='supplier_entry_debit_non_negative'),
            models.CheckConstraint(condition=Q(credit__gte=0), name='supplier_entry_credit_non_negative'),
            models.CheckConstraint(
                condition=(Q(debit__gt=0) & Q(credit=0)) | (Q(credit__gt=0) & Q(debit=0)),
                name='supplier_entry_debit_credit_exclusive',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.supplier.name} - {self.description}'
