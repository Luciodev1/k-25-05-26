import django_filters
from .models import Outflow


class OutflowFilter(django_filters.FilterSet):
    product = django_filters.CharFilter(field_name='product__title', lookup_expr='icontains')
    customer = django_filters.CharFilter(field_name='customer__name', lookup_expr='icontains')

    class Meta:
        model = Outflow
        fields = []
