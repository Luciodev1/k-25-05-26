from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.db.models import F
from .models import Delivery, Outflow
from products.models import Product


def _clear_dashboard_cache(tenant_id):
    key = f'dashboard_{tenant_id or "global"}'
    cache.delete(key)


@receiver(pre_save, sender=Delivery, dispatch_uid='delivery_capture_old_qty')
def capture_old_delivery_quantity(sender, instance, **kwargs):
    """Guarda a final_quantity antiga antes do save para calcular o delta."""
    if instance.pk and not instance._state.adding:
        try:
            old = sender.objects.select_for_update().get(pk=instance.pk)
            instance._old_final_quantity = old.final_quantity
        except sender.DoesNotExist:
            instance._old_final_quantity = 0
    else:
        instance._old_final_quantity = 0


@receiver(post_save, sender=Outflow, dispatch_uid='outflow_clear_dashboard_cache')
def clear_dashboard_on_outflow_save(sender, instance, **kwargs):
    _clear_dashboard_cache(instance.tenant_id)


@receiver(post_save, sender=Delivery, dispatch_uid='delivery_update_stock_save')
def update_stock_on_delivery_save(sender, instance, created, **kwargs):
    _clear_dashboard_cache(instance.tenant_id)
    if created:
        qty = instance.final_quantity
        outflow = Outflow.objects.select_for_update().get(pk=instance.outflow_id)
        product = Product.objects.select_for_update().get(pk=outflow.product_id)

        pending = outflow.quantity - outflow.quantity_delivered
        if qty > pending:
            raise ValidationError(
                f'Quantidade da entrega ({qty}) excede o pendente ({pending}).'
            )
        if qty > product.quantity:
            raise ValidationError(
                f'Stock insuficiente: {product.quantity} disponível, {qty} solicitado.'
            )

        outflow.quantity_delivered = F('quantity_delivered') + qty
        outflow.save(update_fields=['quantity_delivered'])
        outflow.refresh_from_db(fields=['quantity_delivered', 'quantity'])
        outflow.update_status()

        product.quantity = F('quantity') - qty
        product.save()
    else:
        old_qty = getattr(instance, '_old_final_quantity', 0)
        new_qty = instance.final_quantity
        delta = new_qty - old_qty

        if delta != 0:
            outflow = Outflow.objects.select_for_update().get(pk=instance.outflow_id)
            product = Product.objects.select_for_update().get(pk=outflow.product_id)

            outflow.quantity_delivered = F('quantity_delivered') + delta
            outflow.save(update_fields=['quantity_delivered'])
            outflow.refresh_from_db(fields=['quantity_delivered', 'quantity'])
            outflow.update_status()

            product.quantity = F('quantity') - delta
            product.save()


@receiver(post_delete, sender=Delivery, dispatch_uid='delivery_update_stock_hard_delete')
def update_stock_on_delivery_hard_delete(sender, instance, **kwargs):
    """Apenas para hard-delete sem passar por Delivery.delete() (stock já tratado no modelo)."""
    if getattr(instance, '_stock_handled', False) or instance.is_deleted:
        return
    _clear_dashboard_cache(instance.tenant_id)
    outflow = instance.outflow
    product = outflow.product
    qty = instance.final_quantity
    outflow.quantity_delivered = F('quantity_delivered') - qty
    outflow.save(update_fields=['quantity_delivered'])
    outflow.refresh_from_db(fields=['quantity_delivered', 'quantity'])
    outflow.update_status()
    product.quantity = F('quantity') + qty
    product.save()
