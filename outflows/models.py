from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db.models import F
from django.db.models.expressions import BaseExpression
from django.utils import timezone
from products.models import Product
from customers.models import Customer
from drivers.models import Driver
from app.mixins import SoftDeleteModel
from app.validators import validate_file_content
from audit.signals import log_action


def validate_file_size(value):
    """Valida que o arquivo nao excede 10 MB."""
    limit = 10 * 1024 * 1024  # 10 MB
    if value.size > limit:
        raise ValidationError('O arquivo nao pode exceder 10 MB.')


class Outflow(SoftDeleteModel):
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('partial', 'Parcial'),
        ('delivered', 'Entregue'),
    ]

    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='outflows', null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='outflows', verbose_name='Produto')
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='outflows', verbose_name='Cliente')
    quantity = models.DecimalField(
        max_digits=20, decimal_places=4,
        validators=[MinValueValidator(0.0001)], verbose_name='Quantidade',
    )
    quantity_delivered = models.DecimalField(max_digits=20, decimal_places=4, default=0, db_index=True, verbose_name='Quantidade Entregue')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True,
        verbose_name='Estado',
    )
    price = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)], verbose_name='Preço de Saída')
    description = models.TextField(null=True, blank=True, verbose_name='Descrição')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Saída'
        verbose_name_plural = 'Saídas'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'created_at']),
            models.Index(fields=['product', 'created_at']),
            models.Index(fields=['tenant', 'is_deleted']),
            models.Index(fields=['tenant', 'created_at']),
            models.Index(fields=['tenant', 'customer']),
            models.Index(fields=['tenant', 'product']),
            models.Index(fields=['tenant', 'status']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name='outflow_quantity_positive',
            ),
            models.CheckConstraint(
                condition=models.Q(quantity_delivered__gte=0),
                name='outflow_quantity_delivered_non_negative',
            ),
        ]

    def _compute_status(self):
        """Devolve a chave do estado actual (pending/partial/delivered)."""
        if self.quantity_delivered == 0:
            return 'pending'
        elif self.quantity_delivered < self.quantity:
            return 'partial'
        return 'delivered'

    def save(self, *args, **kwargs):
        # If quantity_delivered is a database expression (e.g. F()),
        # skip status computation — caller must refresh and call update_status.
        if isinstance(self.quantity_delivered, BaseExpression):
            super().save(*args, **kwargs)
        else:
            self.status = self._compute_status()
            super().save(*args, **kwargs)

    def update_status(self):
        """Actualiza o campo status com base nos valores actuais de quantity e quantity_delivered."""
        self.status = self._compute_status()
        self.save(update_fields=['status'])

    def __str__(self):
        return f'{self.product} - {self.customer} ({self.quantity})'

    def delete(self, using=None, keep_parents=False):
        with transaction.atomic():
            from accounts.models import CustomerAccountEntry
            CustomerAccountEntry.objects.filter(outflow=self, tenant=self.tenant).delete()

            for delivery in self.deliveries.select_for_update().all():
                delivery.delete()

            self.quantity_delivered = 0
            self.save(update_fields=['quantity_delivered', 'status'])

            log_action(self, 'DELETE')
            super().delete(using=using, keep_parents=keep_parents)

    @property
    def quantity_pending(self):
        return self.quantity - self.quantity_delivered

    @property
    def status_display(self):
        """Valor de exibição do estado (ex: 'Pendente')."""
        return self.get_status_display()


class Delivery(SoftDeleteModel):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='deliveries', null=True, blank=True)
    outflow = models.ForeignKey(Outflow, on_delete=models.PROTECT, related_name='deliveries')
    driver = models.ForeignKey(
        Driver, on_delete=models.PROTECT, related_name='deliveries',
        verbose_name='Motorista', null=True, blank=True,
    )
    quantity = models.DecimalField(
        max_digits=20, decimal_places=4, verbose_name='Quantidade Estimada',
        validators=[MinValueValidator(0.0001)],
    )
    actual_quantity = models.DecimalField(
        max_digits=20, decimal_places=4, verbose_name='Quantidade Real (Balança)',
        null=True, blank=True, validators=[MinValueValidator(0)],
    )
    is_confirmed = models.BooleanField(default=False, verbose_name='Confirmado na Balança')
    delivery_date = models.DateField(verbose_name='Data de Entrega', null=True, blank=True)
    shipping_guide_number = models.CharField(max_length=100, verbose_name='Nº Guia de Remessa', null=True, blank=True)
    shipping_guide_file = models.FileField(
        upload_to='shipping_guides/', null=True, blank=True, verbose_name='Anexo da Guia',
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png']),
            validate_file_size,
            validate_file_content,
        ],
    )
    invoice_number = models.CharField(max_length=100, verbose_name='Nº da Factura Associada', null=True, blank=True)
    origin = models.CharField(max_length=200, verbose_name='Origem do Produto', null=True, blank=True)
    destination = models.CharField(max_length=200, verbose_name='Local da Entrega', null=True, blank=True)
    receiver_name = models.CharField(max_length=200, verbose_name='Nome do Receptor', null=True, blank=True)
    description = models.TextField(null=True, blank=True, verbose_name='Descrição')
    delivered_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Entrega'
        verbose_name_plural = 'Entregas'
        ordering = ['-delivered_at']
        indexes = [
            models.Index(fields=['outflow', 'delivered_at']),
            models.Index(fields=['driver', 'delivered_at']),
            models.Index(fields=['tenant', 'is_deleted']),
            models.Index(fields=['tenant', 'delivered_at']),
            models.Index(fields=['tenant', 'driver']),
            models.Index(fields=['tenant', 'outflow']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name='delivery_quantity_positive',
            ),
        ]

    def __str__(self):
        return f'{self.outflow} - {self.final_quantity}'

    @property
    def final_quantity(self):
        if self.is_confirmed and self.actual_quantity is not None:
            return self.actual_quantity
        return self.quantity

    def _adjust_stock_on_remove(self):
        """Restaura stock e decrementa quantity_delivered (operação inversa à entrega)."""
        qty = self.final_quantity
        outflow = Outflow.objects.select_for_update().get(pk=self.outflow_id)
        product = Product.objects.select_for_update().get(pk=outflow.product_id)
        product.quantity = F('quantity') + qty
        product.save(update_fields=['quantity'])
        product.refresh_from_db(fields=['quantity'])
        outflow.quantity_delivered = F('quantity_delivered') - qty
        outflow.save(update_fields=['quantity_delivered'])
        outflow.refresh_from_db(fields=['quantity_delivered'])

    def _adjust_stock_on_restore(self):
        """Reaplica dedução de stock ao restaurar entrega."""
        qty = self.final_quantity
        outflow = Outflow.objects.select_for_update().get(pk=self.outflow_id)
        product = Product.objects.select_for_update().get(pk=outflow.product_id)
        if qty > outflow.quantity_pending:
            raise ValidationError(
                f'Não é possível restaurar: quantidade ({qty}) excede pendente ({outflow.quantity_pending}).'
            )
        if qty > product.quantity:
            raise ValidationError(
                f'Não é possível restaurar: stock insuficiente ({product.quantity}).'
            )
        product.quantity = F('quantity') - qty
        product.save(update_fields=['quantity'])
        outflow.quantity_delivered = F('quantity_delivered') + qty
        outflow.save(update_fields=['quantity_delivered'])

    def delete(self, using=None, keep_parents=False):
        """Soft delete atómico com restauro de stock."""
        if self.is_deleted:
            return
        with transaction.atomic():
            Delivery.objects.select_for_update().filter(pk=self.pk)
            self._stock_handled = True
            self._adjust_stock_on_remove()
            log_action(self, 'DELETE')
            now = timezone.now()
            type(self).all_objects.filter(pk=self.pk).update(
                is_deleted=True, deleted_at=now,
            )
            self.is_deleted = True
            self.deleted_at = now

    def restore(self):
        """Restaura entrega eliminada e reaplica movimento de stock."""
        if not self.is_deleted:
            return
        with transaction.atomic():
            type(self).all_objects.select_for_update().filter(pk=self.pk)
            self._adjust_stock_on_restore()
            type(self).all_objects.filter(pk=self.pk).update(
                is_deleted=False, deleted_at=None,
            )
            self.is_deleted = False
            self.deleted_at = None

    def hard_delete(self, using=None, keep_parents=False):
        """Eliminação física (apenas para lixo permanente)."""
        with transaction.atomic():
            if not self.is_deleted:
                self._stock_handled = True
                self._adjust_stock_on_remove()
            super(SoftDeleteModel, self).delete(using=using, keep_parents=keep_parents)
