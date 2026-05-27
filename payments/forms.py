from decimal import Decimal

from django import forms
from django.core.validators import MinValueValidator
from .models import Payment


class PaymentForm(forms.ModelForm):
    amount = forms.DecimalField(
        max_digits=20, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        label='Valor',
    )

    class Meta:
        model = Payment
        fields = ['type', 'customer', 'supplier', 'amount', 'payment_method', 'date', 'description']
        widgets = {
            'type': forms.Select(attrs={'class': 'form-select', 'id': 'id_type'}),
            'customer': forms.Select(attrs={'class': 'form-select', 'id': 'id_customer'}),
            'supplier': forms.Select(attrs={'class': 'form-select', 'id': 'id_supplier'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        if tenant:
            self.fields['customer'].queryset = self.fields['customer'].queryset.filter(tenant=tenant)
            self.fields['supplier'].queryset = self.fields['supplier'].queryset.filter(tenant=tenant)

    def clean_date(self):
        from app.validators import validate_payment_date
        date = self.cleaned_data.get('date')
        if date:
            validate_payment_date(date)
        return date

    def clean(self):
        cleaned_data = super().clean()
        payment_type = cleaned_data.get('type')
        customer = cleaned_data.get('customer')
        supplier = cleaned_data.get('supplier')

        if payment_type == 'RECEIPT' and not customer:
            self.add_error('customer', 'Selecione um cliente para o recebimento.')
        if payment_type == 'PAYMENT' and not supplier:
            self.add_error('supplier', 'Selecione um fornecedor para o pagamento.')
        return cleaned_data
