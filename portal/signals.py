import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils import timezone

from outflows.models import Outflow, Delivery
from payments.models import Payment
from portal.models import CustomerAccess

logger = logging.getLogger(__name__)


def _get_email_for_customer(customer):
    if customer.email:
        return customer.email
    try:
        access = CustomerAccess.objects.select_related('user').get(
            customer=customer, is_active=True, is_deleted=False,
        )
        return access.user.email
    except CustomerAccess.DoesNotExist:
        return None


def _send_notification(recipient_email, subject, template, context):
    if not recipient_email:
        return
    try:
        html = render_to_string(template, context)
        send_mail(
            subject=subject,
            message='',
            html_message=html,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=True,
        )
    except Exception as exc:
        logger.warning('Falha ao enviar email de notificação: %s', exc, exc_info=True)


@receiver(post_save, sender=Outflow, dispatch_uid='portal_notify_outflow')
def notify_outflow_created(sender, instance, created, **kwargs):
    if not created or instance.is_deleted:
        return
    customer = instance.customer
    email = _get_email_for_customer(customer)
    if not email:
        return
    _send_notification(
        recipient_email=email,
        subject=f'Nova saída registada - {instance.product.title}',
        template='portal/email_outflow.html',
        context={
            'customer': customer,
            'outflow': instance,
            'product': instance.product,
            'date': timezone.now(),
            'company': settings.COMPANY_INFO['NAME'],
        },
    )


@receiver(pre_save, sender=Delivery, dispatch_uid='portal_delivery_capture_state')
def capture_delivery_state(sender, instance, **kwargs):
    if instance.pk and not instance._state.adding:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._old_is_confirmed = old.is_confirmed
        except sender.DoesNotExist:
            instance._old_is_confirmed = False
    else:
        instance._old_is_confirmed = False


@receiver(post_save, sender=Delivery, dispatch_uid='portal_notify_delivery')
def notify_delivery_created(sender, instance, created, **kwargs):
    if instance.is_deleted:
        return
    was_confirmed = getattr(instance, '_old_is_confirmed', False)
    should_notify = created or (instance.is_confirmed and not was_confirmed)
    if not should_notify:
        return
    customer = instance.outflow.customer
    email = _get_email_for_customer(customer)
    if not email:
        return
    subject = f'Entrega {"confirmada" if instance.is_confirmed else "registada"} - {instance.outflow.product.title}'
    _send_notification(
        recipient_email=email,
        subject=subject,
        template='portal/email_delivery.html',
        context={
            'customer': customer,
            'delivery': instance,
            'outflow': instance.outflow,
            'product': instance.outflow.product,
            'date': timezone.now(),
            'company': settings.COMPANY_INFO['NAME'],
        },
    )


@receiver(post_save, sender=Payment, dispatch_uid='portal_notify_payment')
def notify_payment_received(sender, instance, created, **kwargs):
    if instance.is_deleted or instance.type != 'RECEIPT' or not instance.customer:
        return
    if not created:
        return
    customer = instance.customer
    email = _get_email_for_customer(customer)
    if not email:
        return
    _send_notification(
        recipient_email=email,
        subject=f'Pagamento recebido - {instance.amount:.2f} Kz',
        template='portal/email_payment.html',
        context={
            'customer': customer,
            'payment': instance,
            'date': timezone.now(),
            'company': settings.COMPANY_INFO['NAME'],
        },
    )
