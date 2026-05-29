from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.db.models import F
from .models import Inflow


@receiver(pre_save, sender=Inflow, dispatch_uid='inflow_capture_old_state')
def capture_old_inflow_state(sender, instance, **kwargs):
    """
    Guarda a quantidade e o estado is_deleted antes do save,
    para calcular deltas e detectar transições de soft-delete / restauro.
    """
    if instance.pk and not instance._state.adding:
        try:
            old = sender.all_objects.get(pk=instance.pk)
            instance._old_quantity = old.quantity
            instance._was_deleted = old.is_deleted
        except sender.DoesNotExist:
            instance._old_quantity = 0
            instance._was_deleted = False
    else:
        instance._old_quantity = 0
        instance._was_deleted = False


@receiver(post_save, sender=Inflow, dispatch_uid='inflow_update_stock_save')
def update_stock_on_inflow_save(sender, instance, created, **kwargs):
    """
    Gere todas as transições de stock num único ponto:

    1. Criação         → adiciona stock
    2. Soft-delete     → subtrai stock  (was_deleted=False → is_deleted=True)
    3. Restauro        → devolve stock  (was_deleted=True  → is_deleted=False)
    4. Edição normal   → aplica delta (nova_qty - antiga_qty)
    """
    product = instance.product
    was_deleted = getattr(instance, '_was_deleted', False)

    if created:
        # 1. Nova entrada: acrescentar ao stock
        product.quantity = F('quantity') + instance.quantity
        product.save(update_fields=['quantity'])

    elif not was_deleted and instance.is_deleted:
        # 2. Soft-delete: subtrair do stock
        product.quantity = F('quantity') - instance.quantity
        product.save(update_fields=['quantity'])

    elif was_deleted and not instance.is_deleted:
        # 3. Restauro: devolver stock que foi subtraído
        product.quantity = F('quantity') + instance.quantity
        product.save(update_fields=['quantity'])

    else:
        # 4. Edição de quantidade: aplicar apenas o delta
        old_qty = getattr(instance, '_old_quantity', 0)
        delta = instance.quantity - old_qty
        if delta != 0:
            product.quantity = F('quantity') + delta
            product.save(update_fields=['quantity'])


@receiver(post_delete, sender=Inflow, dispatch_uid='inflow_update_stock_hard_delete')
def update_stock_on_inflow_hard_delete(sender, instance, **kwargs):
    """
    Dispara apenas no hard-delete (eliminação física da base de dados).
    Só subtrai o stock se o registo NÃO estiver já em soft-delete
    (se estiver, o stock já foi ajustado no post_save do soft-delete).
    """
    if not instance.is_deleted:
        product = instance.product
        product.quantity = F('quantity') - instance.quantity
        product.save(update_fields=['quantity'])
