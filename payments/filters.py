import django_filters
from .models import Payment


class PaymentFilter(django_filters.FilterSet):
    type = django_filters.ChoiceFilter(choices=Payment.TYPE_CHOICES)
    method = django_filters.ChoiceFilter(
        field_name='payment_method', choices=Payment.METHOD_CHOICES
    )

    class Meta:
        model = Payment
        fields = []
