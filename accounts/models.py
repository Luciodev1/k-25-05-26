from django.db import models
from django.db.models import Q
from customers.models import Customer
from suppliers.models import Supplier
from outflows.models import Outflow
from inflows.models import Inflow


class CustomerAccountEntry(models.Model):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, null=True, blank=True, related_name='customer_account_entries')
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='account_entries')
    outflow = models.ForeignKey(Outflow, on_delete=models.SET_NULL, null=True, blank=True, related_name='account_entries')
    payment = models.ForeignKey('payments.Payment', on_delete=models.SET_NULL, null=True, blank=True, related_name='customer_account_entries')
    date = models.DateTimeField(auto_now_add=True, db_index=True)
    description = models.CharField(max_length=500)
    debit = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Customer Account Entry'
        verbose_name_plural = 'Customer Account Entries'
        ordering = ['-date']
        indexes = [
            models.Index(fields=['customer', 'date']),
            models.Index(fields=['customer', 'outflow']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(debit__gte=0),
                name='customer_entry_debit_non_negative',
            ),
            models.CheckConstraint(
                condition=Q(credit__gte=0),
                name='customer_entry_credit_non_negative',
            ),
            models.CheckConstraint(
                condition=(
                    (Q(debit__gt=0) & Q(credit=0)) |
                    (Q(credit__gt=0) & Q(debit=0))
                ),
                name='customer_entry_debit_credit_exclusive',
            ),
        ]

    def __str__(self):
        return f'{self.customer.name} - {self.description}'


class SupplierAccountEntry(models.Model):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, null=True, blank=True, related_name='supplier_account_entries')
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='account_entries')
    inflow = models.ForeignKey(Inflow, on_delete=models.SET_NULL, null=True, blank=True, related_name='account_entries')
    payment = models.ForeignKey('payments.Payment', on_delete=models.SET_NULL, null=True, blank=True, related_name='supplier_account_entries')
    date = models.DateTimeField(auto_now_add=True, db_index=True)
    description = models.CharField(max_length=500)
    debit = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Supplier Account Entry'
        verbose_name_plural = 'Supplier Account Entries'
        ordering = ['-date']
        indexes = [
            models.Index(fields=['supplier', 'date']),
            models.Index(fields=['supplier', 'inflow']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(debit__gte=0),
                name='supplier_entry_debit_non_negative',
            ),
            models.CheckConstraint(
                condition=Q(credit__gte=0),
                name='supplier_entry_credit_non_negative',
            ),
            models.CheckConstraint(
                condition=(
                    (Q(debit__gt=0) & Q(credit=0)) |
                    (Q(credit__gt=0) & Q(debit=0))
                ),
                name='supplier_entry_debit_credit_exclusive',
            ),
        ]

    def __str__(self):
        return f'{self.supplier.name} - {self.description}'
