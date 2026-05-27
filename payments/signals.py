from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from .models import Payment
from accounts.models import CustomerAccountEntry, SupplierAccountEntry


@receiver(post_save, sender=Payment)
def sync_account_entry_on_payment(sender, instance, created, **kwargs):
    """
    Sincroniza o lançamento de conta com o estado actual do Pagamento.

    - Soft-delete: apaga o lançamento existente.
    - Criação / Restauro / Edição: cria ou actualiza o lançamento (update_or_create).
    """
    if instance.is_deleted:
        # Registo eliminado: remover lançamentos associados
        if instance.type == 'RECEIPT':
            CustomerAccountEntry.objects.filter(payment=instance).delete()
        else:
            SupplierAccountEntry.objects.filter(payment=instance).delete()
        return

    if instance.type == 'RECEIPT' and instance.customer:
        CustomerAccountEntry.objects.update_or_create(
            payment=instance,
            defaults={
                'customer': instance.customer,
                'tenant': instance.tenant,
                'description': (
                    f'Pagamento Recebido - {instance.get_payment_method_display()}'
                    f' ({instance.description or ""})'
                ),
                'debit': 0,
                'credit': instance.amount,
            },
        )
    elif instance.type == 'PAYMENT' and instance.supplier:
        SupplierAccountEntry.objects.update_or_create(
            payment=instance,
            defaults={
                'supplier': instance.supplier,
                'tenant': instance.tenant,
                'description': (
                    f'Pagamento Efetuado - {instance.get_payment_method_display()}'
                    f' ({instance.description or ""})'
                ),
                'debit': instance.amount,
                'credit': 0,
            },
        )


@receiver(pre_delete, sender=Payment)
def delete_account_entry_on_payment_delete(sender, instance, **kwargs):
    """Limpeza ao fazer hard-delete de um Pagamento."""
    if instance.type == 'RECEIPT':
        CustomerAccountEntry.objects.filter(payment=instance).delete()
    else:
        SupplierAccountEntry.objects.filter(payment=instance).delete()



