import django_filters
from .models import Brand


class BrandFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')

    class Meta:
        model = Brand
        fields = []
