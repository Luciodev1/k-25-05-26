from django import forms
from . import models


class ProductForm(forms.ModelForm):

    class Meta:
        model = models.Product
        fields = ['title', 'category', 'brand', 'description', 'serial_number', 'cost_price', 'selling_price', 'quantity']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'brand': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 'any'}),
        }
        labels = {
            'title': 'Título',
            'category': 'Categoria',
            'brand': 'Marca',
            'description': 'Descrição',
            'serial_number': 'Nº de Série',
            'cost_price': 'Preço de Custo',
            'selling_price': 'Preço de Venda',
            'quantity': 'Quantidade em Estoque',
        }

    def __init__(self, *args, **kwargs):
        tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        if tenant:
            self.fields['category'].queryset = self.fields['category'].queryset.filter(tenant=tenant)
            self.fields['brand'].queryset = self.fields['brand'].queryset.filter(tenant=tenant)

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity is not None and quantity <= 0:
            raise forms.ValidationError('A quantidade deve ser maior que zero.')
        return quantity

    def save(self, commit=True):
        from django.db import IntegrityError
        try:
            return super().save(commit=commit)
        except IntegrityError:
            raise forms.ValidationError({'serial_number': 'Já existe um produto com este número de série.'})
