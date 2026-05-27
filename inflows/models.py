from django.db import models, transaction
from django.core.validators import MinValueValidator
from django.db.models import F
from suppliers.models import Supplier
from products.models import Product
from app.mixins import SoftDeleteModel


class Inflow(SoftDeleteModel):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, null=True, blank=True, related_name='inflows')
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='inflows', verbose_name='Fornecedor')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='inflows', verbose_name='Produto')
    quantity = models.DecimalField(
        max_digits=20, decimal_places=4,
        validators=[MinValueValidator(0.0001)], verbose_name='Quantidade',
    )
    price = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name='Preço de Custo')
    description = models.TextField(null=True, blank=True, verbose_name='Descrição')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Entrada'
        verbose_name_plural = 'Entradas'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['supplier', 'created_at']),
            models.Index(fields=['product', 'created_at']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name='inflow_quantity_positive',
            ),
        ]

    def __str__(self):
        return str(self.product)

    def delete(self, using=None, keep_parents=False):
        with transaction.atomic():
            from accounts.models import SupplierAccountEntry
            tenant_filter = {}
            if self.tenant_id:
                tenant_filter['tenant'] = self.tenant
            SupplierAccountEntry.objects.filter(inflow=self, **tenant_filter).delete()
            from audit.signals import log_action
            log_action(self, 'DELETE')
            super().delete(using=using, keep_parents=keep_parents)