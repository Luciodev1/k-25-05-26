import json
import logging
from decimal import Decimal
from django.shortcuts import render
from django.db.models import Sum, F, Value, DecimalField, ExpressionWrapper, Count
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from products.models import Product
from suppliers.models import Supplier
from customers.models import Customer
from inflows.models import Inflow
from outflows.models import Outflow, Delivery
from accounts.models import CustomerAccountEntry, SupplierAccountEntry

logger = logging.getLogger(__name__)


def health_check(request):
    from django.conf import settings
    from django.db import connection
    db_ok = False
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            db_ok = cursor.fetchone() is not None
    except Exception as e:
        logger.exception('Health check DB failed')
        return JsonResponse({'status': 'unhealthy', 'database': 'error'}, status=503)
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
        'version': getattr(settings, 'APP_VERSION', '1.0.0'),
    })


def custom_404(request, exception):
    logger.warning("404: %s - %s", request.path, exception)
    return render(request, '404.html', status=404)


def custom_403(request, exception):
    logger.warning("403: %s - %s", request.path, exception)
    return render(request, '403.html', status=403)


def custom_500(request):
    logger.error("500: %s", request.path, exc_info=True)
    return render(request, '500.html', status=500)


@login_required
def dashboard(request):
    from django.core.cache import cache

    tenant = getattr(request, 'tenant', None)
    tenant_id = getattr(tenant, 'id', 'global')
    cache_key = f'dashboard_{tenant_id}'
    cached = cache.get(cache_key)
    if cached is not None:
        return render(request, 'home.html', cached)

    today = timezone.now()
    first_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

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
        base_outflow.values('customer__id', 'customer__name')
        .annotate(total=Sum(F('quantity') * F('price'), output_field=DecimalField(max_digits=30, decimal_places=2)))
        .order_by('-total')[:5]
    )

    low_stock_products = list(base_product.filter(quantity__lte=10).order_by('quantity')[:5])

    price_agg = base_product.aggregate(
        total_cost=Coalesce(
            Sum(ExpressionWrapper(F('quantity') * F('cost_price'), output_field=DecimalField(max_digits=30, decimal_places=2))),
            Value(Decimal('0')),
            output_field=DecimalField(max_digits=30, decimal_places=2),
        ),
        total_sell=Coalesce(
            Sum(ExpressionWrapper(F('quantity') * F('selling_price'), output_field=DecimalField(max_digits=30, decimal_places=2))),
            Value(Decimal('0')),
            output_field=DecimalField(max_digits=30, decimal_places=2),
        ),
    )
    total_cost = price_agg['total_cost']
    total_sell = price_agg['total_sell']
    margin_pct = ((total_sell - total_cost) / total_sell * 100) if total_sell else Decimal('0')

    from dateutil.relativedelta import relativedelta
    six_months_ago = first_of_month - relativedelta(months=6)
    
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

    cache.set(cache_key, context, 300)

    return render(request, 'home.html', context)


def service_worker(request):
    from django.conf import settings
    from pathlib import Path
    sw_path = Path(settings.STATIC_ROOT or settings.BASE_DIR / 'app' / 'static') / 'js' / 'service-worker.js'
    # Fallback: look in app/static if STATIC_ROOT not set (dev mode)
    if not sw_path.exists():
        sw_path = settings.BASE_DIR / 'app' / 'static' / 'js' / 'service-worker.js'
    with open(sw_path, 'r', encoding='utf-8') as f:
        content = f.read()
    from django.http import HttpResponse
    return HttpResponse(content, content_type='application/javascript')


def pwa_manifest(request):
    tenant = getattr(request, 'tenant', None)
    name = getattr(tenant, 'name', 'SGE') if tenant else 'SGE'
    return JsonResponse({
        'name': f'{name} - Portal do Cliente',
        'short_name': 'SGE Portal',
        'description': 'Sistema de Gestão de Stocks e Contas - Portal do Cliente',
        'start_url': '/portal/',
        'scope': '/',
        'display': 'standalone',
        'orientation': 'portrait-primary',
        'background_color': '#0b1120',
        'theme_color': '#059669',
        'lang': 'pt-PT',
        'icons': [
            {
                'src': f'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><rect width="512" height="512" rx="100" fill="%23059669"/><text x="256" y="360" font-size="300" font-weight="bold" text-anchor="middle" fill="white" font-family="Arial">K</text></svg>',
                'sizes': '512x512',
                'type': 'image/svg+xml',
                'purpose': 'any maskable',
            },
        ],
        'categories': ['business', 'finance'],
    }, content_type='application/manifest+json')


@login_required
def pending_deliveries_stat(request):
    tenant = getattr(request, 'tenant', None)
    qs = Outflow.objects.filter(quantity_delivered__lt=F('quantity'))
    if tenant:
        qs = qs.filter(tenant=tenant)
    count = qs.count()
    return render(request, '_pending_deliveries_stat.html', {'count': count})
