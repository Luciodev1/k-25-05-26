from decimal import Decimal

from django import forms
from django.core.validators import MinValueValidator
from django.db.models import Q
from payments.models import Payment
from .models import CustomerAccountEntry, SupplierAccountEntry


class CustomerAccountEntryForm(forms.ModelForm):
    debit = forms.DecimalField(
        max_digits=20, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        label='Débito',
    )
    credit = forms.DecimalField(
        max_digits=20, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        label='Crédito',
    )

    class Meta:
        model = CustomerAccountEntry
        fields = ['description', 'debit', 'credit']
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'description': 'Descrição',
        }

    def clean(self):
        cleaned_data = super().clean()
        debit = cleaned_data.get('debit') or 0
        credit = cleaned_data.get('credit') or 0
        if debit > 0 and credit > 0:
            raise forms.ValidationError('Débito e crédito não podem ser ambos positivos.')
        if debit == 0 and credit == 0:
            raise forms.ValidationError('Débito ou crédito deve ser maior que zero.')
        return cleaned_data


class SupplierAccountEntryForm(forms.ModelForm):
    debit = forms.DecimalField(
        max_digits=20, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        label='Débito',
    )
    credit = forms.DecimalField(
        max_digits=20, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        label='Crédito',
    )

    class Meta:
        model = SupplierAccountEntry
        fields = ['description', 'debit', 'credit']
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'description': 'Descrição',
        }

    def clean(self):
        cleaned_data = super().clean()
        debit = cleaned_data.get('debit') or 0
        credit = cleaned_data.get('credit') or 0
        if debit > 0 and credit > 0:
            raise forms.ValidationError('Débito e crédito não podem ser ambos positivos.')
        if debit == 0 and credit == 0:
            raise forms.ValidationError('Débito ou crédito deve ser maior que zero.')
        return cleaned_data


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

