import django_filters
from .models import Driver


class DriverFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')

    class Meta:
        model = Driver
        fields = []
