import django_filters
from outflows.models import Outflow, Delivery
from inflows.models import Inflow
from payments.models import Payment
from products.models import Product


class BaseReportFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name='created_at', lookup_expr='gte', label='De')
    date_to = django_filters.DateFilter(field_name='created_at', lookup_expr='lte', label='Até')


class OutflowReportFilter(BaseReportFilter):
    customer = django_filters.NumberFilter(field_name='customer_id')
    status = django_filters.CharFilter(method='filter_status')

    class Meta:
        model = Outflow
        fields = ['customer', 'date_from', 'date_to']

    def filter_status(self, queryset, name, value):
        from django.db.models import F
        if value == 'pending':
            return queryset.filter(quantity_delivered=0)
        if value == 'partial':
            return queryset.filter(quantity_delivered__gt=0, quantity_delivered__lt=F('quantity'))
        if value == 'delivered':
            return queryset.filter(quantity_delivered__gte=F('quantity'))
        return queryset


class InflowReportFilter(BaseReportFilter):
    supplier = django_filters.NumberFilter(field_name='supplier_id')

    class Meta:
        model = Inflow
        fields = ['supplier', 'date_from', 'date_to']


class PaymentReportFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name='date', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='date', lookup_expr='lte')
    payment_method = django_filters.ChoiceFilter(choices=Payment.METHOD_CHOICES)

    class Meta:
        model = Payment
        fields = ['payment_method', 'date_from', 'date_to']


class StockReportFilter(django_filters.FilterSet):
    category = django_filters.NumberFilter(field_name='category_id')
    low_stock = django_filters.BooleanFilter(method='filter_low_stock', label='Stock baixo')

    class Meta:
        model = Product
        fields = ['category', 'low_stock']

    def filter_low_stock(self, queryset, name, value):
        if value:
            return queryset.filter(quantity__lte=10)
        return queryset
