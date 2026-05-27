from django import forms
from . import models


class OutflowForm(forms.ModelForm):

    class Meta:
        model = models.Outflow
        fields = ['product', 'customer', 'quantity', 'price', 'description']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0.0001', 'step': 'any'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'product': 'Produto',
            'customer': 'Cliente',
            'quantity': 'Quantidade',
            'price': 'Preço de Saída (Opcional)',
            'description': 'Descrição',
        }

    def __init__(self, *args, **kwargs):
        tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        if tenant:
            self.fields['product'].queryset = self.fields['product'].queryset.filter(tenant=tenant)
            self.fields['customer'].queryset = self.fields['customer'].queryset.filter(tenant=tenant)

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity is not None and quantity <= 0:
            raise forms.ValidationError('A quantidade deve ser maior que zero.')
        return quantity

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        quantity = cleaned_data.get('quantity')
        if product and quantity and quantity > product.quantity:
            raise forms.ValidationError(
                f'Quantidade ({quantity}) excede o estoque disponivel ({product.quantity}).'
            )
        return cleaned_data


class DeliveryForm(forms.ModelForm):

    class Meta:
        model = models.Delivery
        fields = [
            'delivery_date', 'driver', 'quantity',
            'shipping_guide_number', 'shipping_guide_file',
            'invoice_number', 'origin', 'destination',
            'receiver_name', 'description'
        ]
        widgets = {
            'delivery_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'driver': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0.0001', 'step': 'any'}),
            'shipping_guide_number': forms.TextInput(attrs={'class': 'form-control'}),
            'shipping_guide_file': forms.FileInput(attrs={'class': 'form-control'}),
            'invoice_number': forms.TextInput(attrs={'class': 'form-control'}),
            'origin': forms.TextInput(attrs={'class': 'form-control'}),
            'destination': forms.TextInput(attrs={'class': 'form-control'}),
            'receiver_name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        if tenant:
            self.fields['driver'].queryset = self.fields['driver'].queryset.filter(tenant=tenant)

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity is not None and quantity <= 0:
            raise forms.ValidationError('A quantidade deve ser maior que zero.')
        return quantity

    def clean_shipping_guide_file(self):
        from app.validators import validate_file_content
        f = self.cleaned_data.get('shipping_guide_file')
        if f:
            validate_file_content(f)
            if f.size > 10 * 1024 * 1024:
                raise forms.ValidationError('O ficheiro nao pode exceder 10 MB.')
        return f
