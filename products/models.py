from django.db import models
from django.core.validators import MinValueValidator
from categories.models import Category
from brands.models import Brand
from app.mixins import SoftDeleteModel
from audit.signals import log_action


class Product(SoftDeleteModel):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='products')
    title = models.CharField(max_length=500, verbose_name='Título')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products', verbose_name='Categoria')
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name='products', verbose_name='Marca')
    description = models.TextField(null=True, blank=True, verbose_name='Descrição')
    serial_number = models.CharField(max_length=200, null=True, blank=True, verbose_name='N.º de Série')
    cost_price = models.DecimalField(max_digits=20, decimal_places=2, verbose_name='Preço de Custo')
    selling_price = models.DecimalField(max_digits=20, decimal_places=2, verbose_name='Preço de Venda')
    quantity = models.DecimalField(
        max_digits=20, decimal_places=4, default=0,
        validators=[MinValueValidator(0)], verbose_name='Quantidade',
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'
        ordering = ['title']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gte=0),
                name='product_quantity_non_negative',
            ),
            models.UniqueConstraint(
                fields=['serial_number'],
                condition=models.Q(serial_number__isnull=False) & ~models.Q(serial_number=''),
                name='product_serial_number_unique',
            ),
        ]

    def __str__(self):
        return self.title

    def delete(self, using=None, keep_parents=False):
        log_action(self, 'DELETE')
        super().delete(using=using, keep_parents=keep_parents)
