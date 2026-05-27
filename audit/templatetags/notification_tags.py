from django import template
from django.db.models import F
from django.core.cache import cache
from decimal import Decimal

register = template.Library()

NOTIFICATIONS_CACHE_KEY = 'sge_notifications'
NOTIFICATIONS_CACHE_TTL = 60  # 60 segundos


class NotificationItem:
    def __init__(self, title, message, url, icon, color):
        self.title = title
        self.message = message
        self.url = url
        self.icon = icon
        self.color = color


class NotificationCollection:
    def __init__(self):
        self.items = []

    @property
    def count(self):
        return len(self.items)


@register.simple_tag(takes_context=True)
def get_notifications(context):
    """Retorna notificacoes reais do sistema."""
    notifs = NotificationCollection()
    request = context.get('request')
    if not request or not request.user.is_authenticated:
        return notifs

    tenant = getattr(request, 'tenant', None)
    items = []

    # 1. Stock baixo (menos de 10 unidades)
    from products.models import Product
    p_base = Product.objects
    if tenant:
        p_base = p_base.filter(tenant=tenant)
    low_stock = p_base.filter(quantity__lte=10, quantity__gt=0).order_by('quantity')[:5]
    for p in low_stock:
        items.append(NotificationItem(
            title='Stock baixo',
            message=f'{p.title} - {p.quantity} unidades restantes',
            url=f'/products/{p.pk}/detail/',
            icon='bi-exclamation-triangle',
            color='text-warning',
        ))

    # 2. Produtos sem stock
    out_of_stock = p_base.filter(quantity__lte=0).count()
    if out_of_stock > 0:
        items.append(NotificationItem(
            title='Produtos sem stock',
            message=f'{out_of_stock} produto(s) esgotado(s)',
            url='/products/list/',
            icon='bi-x-circle',
            color='text-danger',
        ))

    # 3. Entregas pendentes
    from outflows.models import Outflow
    o_base = Outflow.objects
    if tenant:
        o_base = o_base.filter(tenant=tenant)
    pending = o_base.filter(quantity_delivered__lt=F('quantity')).count()
    if pending > 0:
        items.append(NotificationItem(
            title='Entregas pendentes',
            message=f'{pending} saida(s) com entrega pendente',
            url='/outflows/list/',
            icon='bi-truck',
            color='text-info',
        ))

    # 4. Divida de clientes (receber)
    from accounts.models import CustomerAccountEntry, SupplierAccountEntry
    from django.db.models import Sum, Value
    from django.db.models.functions import Coalesce
    ce_base = CustomerAccountEntry.objects
    if tenant:
        ce_base = ce_base.filter(tenant=tenant)
    cust_agg = ce_base.aggregate(
        d=Coalesce(Sum('debit'), Value(Decimal('0'))),
        c=Coalesce(Sum('credit'), Value(Decimal('0'))),
    )
    receivable = cust_agg['d'] - cust_agg['c']
    if receivable > 0:
        items.append(NotificationItem(
            title='Contas a receber',
            message=f'{receivable} Kz por receber de clientes',
            url='/accounts/customer-balances/',
            icon='bi-cash-coin',
            color='text-success',
        ))

    # 5. Divida a fornecedores (pagar)
    se_base = SupplierAccountEntry.objects
    if tenant:
        se_base = se_base.filter(tenant=tenant)
    supp_agg = se_base.aggregate(
        d=Coalesce(Sum('debit'), Value(Decimal('0'))),
        c=Coalesce(Sum('credit'), Value(Decimal('0'))),
    )
    payable = supp_agg['c'] - supp_agg['d']
    if payable > 0:
        items.append(NotificationItem(
            title='Contas a pagar',
            message=f'{payable} Kz a pagar a fornecedores',
            url='/accounts/supplier-balances/',
            icon='bi-credit-card',
            color='text-primary',
        ))

    notifs.items = items
    return notifs
