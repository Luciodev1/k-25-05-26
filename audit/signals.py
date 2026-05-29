import logging
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver
from django.forms.models import model_to_dict

logger = logging.getLogger(__name__)

TRACKED_MODELS = [
    'Product', 'Inflow', 'Outflow', 'Delivery', 'Payment',
    'Customer', 'Supplier', 'Brand', 'Category', 'Driver',
]


def _get_user():
    from audit.middleware import get_current_user
    return get_current_user()


def _get_tracked_fields(instance):
    skip = {'id', 'created_at', 'updated_at', 'password'}
    return [
        f.name for f in instance._meta.get_fields()
        if hasattr(f, 'name') and f.name not in skip and not f.is_relation
    ]


def _get_tenant(instance):
    tenant = getattr(instance, 'tenant', None)
    if tenant is None:
        from audit.middleware import get_current_request
        request = get_current_request()
        if request:
            tenant = getattr(request, 'tenant', None)
    return tenant


def create_audit_log(instance, action, changes=None):
    """Cria entrada de auditoria; falhas nunca interrompem operações de negócio."""
    from audit.models import AuditLog
    try:
        AuditLog.objects.create(
            tenant=_get_tenant(instance),
            user=_get_user(),
            action=action,
            model_name=instance.__class__.__name__,
            object_id=str(instance.pk),
            object_repr=str(instance)[:200],
            changes=changes or {},
        )
    except Exception as exc:
        logger.warning(
            'Falha ao registar auditoria para %s #%s: %s',
            instance.__class__.__name__, instance.pk, exc,
            exc_info=True,
        )


def log_action(instance, action, changes=None):
    """Alias retrocompatível."""
    create_audit_log(instance, action, changes)


def _connect_signals():
    from django.apps import apps
    for model_name in TRACKED_MODELS:
        for model in apps.get_models():
            if model.__name__ == model_name:
                _attach_signals(model)
                break


def _attach_signals(model):
    @receiver(post_save, sender=model, weak=False, dispatch_uid=f'audit_post_save_{model.__name__}')
    def on_save(sender, instance, created, **kwargs):
        try:
            if created:
                create_audit_log(instance, 'CREATE')
            elif hasattr(instance, '_audit_changes'):
                if not getattr(instance, 'is_deleted', False):
                    create_audit_log(instance, 'UPDATE', instance._audit_changes)
                del instance._audit_changes
        except Exception as exc:
            logger.warning('Erro no signal audit post_save: %s', exc, exc_info=True)

    @receiver(pre_save, sender=model, weak=False, dispatch_uid=f'audit_pre_save_{model.__name__}')
    def on_pre_save(sender, instance, **kwargs):
        try:
            if instance.pk and not instance._state.adding:
                try:
                    old = sender.objects.get(pk=instance.pk)
                    changes = {}
                    for field in _get_tracked_fields(instance):
                        old_val = getattr(old, field)
                        new_val = getattr(instance, field)
                        if str(old_val) != str(new_val):
                            changes[field] = {'old': str(old_val), 'new': str(new_val)}
                    if changes:
                        instance._audit_changes = changes
                except sender.DoesNotExist:
                    pass
        except Exception as exc:
            logger.warning('Erro no signal audit pre_save: %s', exc, exc_info=True)

    @receiver(pre_delete, sender=model, weak=False, dispatch_uid=f'audit_pre_delete_{model.__name__}')
    def on_delete(sender, instance, **kwargs):
        try:
            create_audit_log(instance, 'DELETE')
        except Exception as exc:
            logger.warning('Erro no signal audit pre_delete: %s', exc, exc_info=True)


