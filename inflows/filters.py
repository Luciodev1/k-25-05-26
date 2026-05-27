import django_filters
from .models import Inflow


class InflowFilter(django_filters.FilterSet):
    product = django_filters.CharFilter(field_name='product__title', lookup_expr='icontains')
    supplier = django_filters.CharFilter(field_name='supplier__name', lookup_expr='icontains')

    class Meta:
        model = Inflow
        fields = []
