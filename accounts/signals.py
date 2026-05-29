import logging
from decimal import Decimal, ROUND_HALF_UP

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.db import transaction
from outflows.models import Outflow
from inflows.models import Inflow
from .models import CustomerAccountEntry, SupplierAccountEntry

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Outflow, dispatch_uid='accounts_sync_customer_entry')
def sync_customer_account_entry(sender, instance, created, **kwargs):
    """
    Sincroniza o lançamento de conta do cliente com o estado actual da Saída.

    - Soft-delete: apaga o lançamento existente.
    - Criação / Restauro / Edição: cria ou actualiza o lançamento (update_or_create).
    """
    if instance.is_deleted:
        CustomerAccountEntry.objects.filter(outflow=instance).delete()
        return

    price = instance.price or instance.product.selling_price
    if not instance.price:
        logger.warning(
            'Outflow %s sem preço definido, usando selling_price actual do produto (%s). '
            'Isto pode não reflectir o preço no momento da venda.',
            instance.pk, price,
        )
    total = (instance.quantity * price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    try:
        CustomerAccountEntry.objects.update_or_create(
            outflow=instance,
            defaults={
                'customer': instance.customer,
                'tenant': instance.tenant,
                'description': f'Venda - {instance.product.title}(Qtd:{str(instance.quantity.quantize(Decimal("0.01"))).replace(".", ",")})',
                'debit': total,
                'credit': 0,
            },
        )
    except Exception as e:
        logger.error('Erro ao sincronizar lançamento de conta do cliente: %s', e)


@receiver(pre_delete, sender=Outflow, dispatch_uid='accounts_delete_customer_entries')
def delete_customer_entries_on_outflow_delete(sender, instance, **kwargs):
    """Limpeza ao fazer hard-delete de uma Saída."""
    with transaction.atomic():
        CustomerAccountEntry.objects.filter(outflow=instance).delete()


@receiver(post_save, sender=Inflow, dispatch_uid='accounts_sync_supplier_entry')
def sync_supplier_account_entry(sender, instance, created, **kwargs):
    """
    Sincroniza o lançamento de conta do fornecedor com o estado actual da Entrada.

    - Soft-delete: apaga o lançamento existente.
    - Criação / Restauro / Edição: cria ou actualiza o lançamento (update_or_create).
    """
    if instance.is_deleted:
        SupplierAccountEntry.objects.filter(inflow=instance).delete()
        return

    price = instance.price or instance.product.cost_price
    if not instance.price:
        logger.warning(
            'Inflow %s sem preço definido, usando cost_price actual do produto (%s). '
            'Isto pode não reflectir o preço no momento da compra.',
            instance.pk, price,
        )
    total = (instance.quantity * price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    try:
        SupplierAccountEntry.objects.update_or_create(
            inflow=instance,
            defaults={
                'supplier': instance.supplier,
                'tenant': instance.tenant,
                'description': f'Compra - {instance.product.title} (Qtd: {instance.quantity})',
                'debit': 0,
                'credit': total,
            },
        )
    except Exception as e:
        logger.error('Erro ao sincronizar lançamento de conta do fornecedor: %s', e)


@receiver(pre_delete, sender=Inflow, dispatch_uid='accounts_delete_supplier_entries')
def delete_supplier_entries_on_inflow_delete(sender, instance, **kwargs):
    """Limpeza ao fazer hard-delete de uma Entrada."""
    with transaction.atomic():
        SupplierAccountEntry.objects.filter(inflow=instance).delete()



