from decimal import Decimal

from django import forms
from django.core.validators import MinValueValidator
from payments.models import Payment


class CustomerPaymentForm(forms.ModelForm):

    amount = forms.DecimalField(
        max_digits=20, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        label='Valor do Pagamento',
    )

    class Meta:
        model = Payment
        fields = ['customer', 'amount', 'payment_method', 'date', 'description']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'customer': 'Cliente',
            'payment_method': 'Método de Pagamento',
            'date': 'Data',
            'description': 'Descrição',
        }

    def __init__(self, *args, **kwargs):
        tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        self.fields['customer'].disabled = True
        if tenant:
            self.fields['customer'].queryset = self.fields['customer'].queryset.filter(tenant=tenant)


class SupplierPaymentForm(forms.ModelForm):

    amount = forms.DecimalField(
        max_digits=20, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        label='Valor do Pagamento',
    )

    class Meta:
        model = Payment
        fields = ['supplier', 'amount', 'payment_method', 'date', 'description']
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'supplier': 'Fornecedor',
            'payment_method': 'Método de Pagamento',
            'date': 'Data',
            'description': 'Descrição',
        }

    def __init__(self, *args, **kwargs):
        tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        self.fields['supplier'].disabled = True
        if tenant:
            self.fields['supplier'].queryset = self.fields['supplier'].queryset.filter(tenant=tenant)

