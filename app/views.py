import json
import logging
from decimal import Decimal
from django.shortcuts import render
from django.db.models import Sum, F, Value, DecimalField
from django.db.models.functions import Coalesce, TruncMonth
from django.db.models import Count
from django.utils import timezone
from django.http import JsonResponse
from products.models import Product
from suppliers.models import Supplier
from customers.models import Customer
from inflows.models import Inflow
from outflows.models import Outflow, Delivery
from accounts.models import CustomerAccountEntry, SupplierAccountEntry

from django.contrib.auth.decorators import login_required

logger = logging.getLogger(__name__)


def health_check(request):
    from django.db import connection
    db_ok = False
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            db_ok = cursor.fetchone() is not None
    except Exception as e:
        logger.exception('Health check DB failed')
        return JsonResponse({'status': 'unhealthy', 'database': str(e)}, status=503)
    cache_ok = None
    try:
        from django.core.cache import cache
        cache.set('__health__', 'ok', 5)
        cache_ok = cache.get('__health__') == 'ok'
    except Exception:
        cache_ok = False
    return JsonResponse({
        'status': 'healthy' if db_ok else 'unhealthy',
        'database': db_ok,
        'cache': cache_ok,
        'version': '1.0.0',
    })


def custom_404(request, exception):
    logger.warning(f"404: {request.path} - {exception}")
    return render(request, '404.html', status=404)


def custom_500(request):
    logger.error(f"500: {request.path}", exc_info=True)
    return render(request, '500.html', status=500)


@login_required
def dashboard(request):
    today = timezone.now()
    first_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    tenant = getattr(request, 'tenant', None)

    base_product = Product.objects
    base_supplier = Supplier.objects
    base_customer = Customer.objects
    base_inflow = Inflow.objects
    base_outflow = Outflow.objects
    base_delivery = Delivery.objects
    base_customer_entry = CustomerAccountEntry.objects
    base_supplier_entry = SupplierAccountEntry.objects
    if tenant:
        base_product = base_product.filter(tenant=tenant)
        base_supplier = base_supplier.filter(tenant=tenant)
        base_customer = base_customer.filter(tenant=tenant)
        base_inflow = base_inflow.filter(tenant=tenant)
        base_outflow = base_outflow.filter(tenant=tenant)
        base_delivery = base_delivery.filter(tenant=tenant)
        base_customer_entry = base_customer_entry.filter(tenant=tenant)
        base_supplier_entry = base_supplier_entry.filter(tenant=tenant)

    total_products = base_product.count()
    total_suppliers = base_supplier.count()
    total_customers = base_customer.count()
    inflows_this_month = base_inflow.filter(created_at__gte=first_of_month).count()
    outflows_this_month = base_outflow.filter(created_at__gte=first_of_month).count()

    outflows_pending = list(base_outflow.filter(
        quantity_delivered__lt=F('quantity')
    ).select_related('customer', 'product')[:10])

    from django.db.models import ExpressionWrapper
    total_stock_value = base_product.aggregate(
        total=Coalesce(
            Sum(ExpressionWrapper(F('quantity') * F('selling_price'), output_field=DecimalField(max_digits=30, decimal_places=2))),
            Value(Decimal('0')),
            output_field=DecimalField(max_digits=30, decimal_places=2),
        )
    )['total']

    customer_agg = base_customer_entry.aggregate(
        total_debit=Coalesce(Sum('debit'), Value(Decimal('0'))),
        total_credit=Coalesce(Sum('credit'), Value(Decimal('0'))),
    )
    total_receivable = max(Decimal('0'), customer_agg['total_debit'] - customer_agg['total_credit'])
    total_to_regularize = max(Decimal('0'), customer_agg['total_credit'] - customer_agg['total_debit'])

    supplier_agg = base_supplier_entry.aggregate(
        total_debit=Coalesce(Sum('debit'), Value(Decimal('0'))),
        total_credit=Coalesce(Sum('credit'), Value(Decimal('0'))),
    )
    total_supplier_debt = max(Decimal('0'), supplier_agg['total_credit'] - supplier_agg['total_debit'])
    total_supplier_receivable = max(Decimal('0'), supplier_agg['total_debit'] - supplier_agg['total_credit'])

    recent_inflows = list(base_inflow.select_related('product', 'supplier').order_by('-created_at')[:5])
    recent_outflows = list(base_outflow.select_related('product', 'customer').order_by('-created_at')[:5])
    recent_deliveries = list(base_delivery.select_related('outflow__product', 'outflow__customer').order_by('-delivered_at')[:5])

    top_customers = list(
        base_outflow.values('customer__name')
        .annotate(total=Sum(F('quantity') * F('price'), output_field=DecimalField(max_digits=30, decimal_places=2)))
        .order_by('-total')[:5]
    )

    low_stock_products = list(base_product.filter(quantity__lte=10).order_by('quantity')[:5])

    cost_agg = base_product.aggregate(
        total=Coalesce(
            Sum(ExpressionWrapper(F('quantity') * F('cost_price'), output_field=DecimalField(max_digits=30, decimal_places=2))),
            Value(Decimal('0')),
            output_field=DecimalField(max_digits=30, decimal_places=2),
        )
    )
    sell_agg = base_product.aggregate(
        total=Coalesce(
            Sum(ExpressionWrapper(F('quantity') * F('selling_price'), output_field=DecimalField(max_digits=30, decimal_places=2))),
            Value(Decimal('0')),
            output_field=DecimalField(max_digits=30, decimal_places=2),
        )
    )
    total_cost = cost_agg['total']
    total_sell = sell_agg['total']
    margin_pct = ((total_sell - total_cost) / total_cost * 100) if total_cost else Decimal('0')

    six_months_ago = first_of_month - timezone.timedelta(days=150)
    
    inflows_data = base_inflow.filter(created_at__gte=six_months_ago) \
        .annotate(month=TruncMonth('created_at')) \
        .values('month') \
        .annotate(count=Count('id')) \
        .order_by('month')
    
    outflows_data = base_outflow.filter(created_at__gte=six_months_ago) \
        .annotate(month=TruncMonth('created_at')) \
        .values('month') \
        .annotate(count=Count('id')) \
        .order_by('month')

    inflows_map = {d['month'].date(): d['count'] for d in inflows_data}
    outflows_map = {d['month'].date(): d['count'] for d in outflows_data}

    month_labels = []
    inflows_monthly = []
    outflows_monthly = []
    
    for i in range(6):
        m = (today.month - (5 - i) - 1) % 12 + 1
        y = today.year + (today.month - (5 - i) - 1) // 12
        d = today.replace(year=y, month=m, day=1).date()
        
        month_labels.append(d.strftime('%b/%y'))
        inflows_monthly.append(inflows_map.get(d, 0))
        outflows_monthly.append(outflows_map.get(d, 0))

    context = {
        'total_products': total_products,
        'total_suppliers': total_suppliers,
        'total_customers': total_customers,
        'inflows_this_month': inflows_this_month,
        'outflows_this_month': outflows_this_month,
        'outflows_pending': outflows_pending,
        'total_stock_value': total_stock_value,
        'total_receivable': total_receivable,
        'total_to_regularize': total_to_regularize,
        'total_supplier_debt': total_supplier_debt,
        'total_supplier_receivable': total_supplier_receivable,
        'recent_inflows': recent_inflows,
        'recent_outflows': recent_outflows,
        'recent_deliveries': recent_deliveries,
        'month_labels': json.dumps(month_labels),
        'inflows_monthly': json.dumps(inflows_monthly),
        'outflows_monthly': json.dumps(outflows_monthly),
        'top_customers': top_customers,
        'low_stock_products': low_stock_products,
        'margin_pct': round(margin_pct, 1),
    }

    return render(request, 'home.html', context)
