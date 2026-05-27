import django_filters
from .models import Product


class ProductFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(field_name='title', lookup_expr='icontains')
    category = django_filters.NumberFilter(field_name='category_id')
    brand = django_filters.NumberFilter(field_name='brand_id')
    min_price = django_filters.NumberFilter(field_name='selling_price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='selling_price', lookup_expr='lte')
    stock_status = django_filters.ChoiceFilter(
        method='filter_stock_status',
        choices=[('ok', 'Normal'), ('low', 'Baixo'), ('out', 'Esgotado')],
    )
    date_from = django_filters.DateFilter(field_name='created_at__date', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='created_at__date', lookup_expr='lte')

    class Meta:
        model = Product
        fields = []

    def filter_stock_status(self, queryset, name, value):
        if value == 'low':
            return queryset.filter(quantity__lte=10, quantity__gt=0)
        elif value == 'out':
            return queryset.filter(quantity__lte=0)
        elif value == 'ok':
            return queryset.filter(quantity__gt=10)
        return queryset
