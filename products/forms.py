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
        self._tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        if self._tenant:
            self.fields['category'].queryset = self.fields['category'].queryset.filter(tenant=self._tenant)
            self.fields['brand'].queryset = self.fields['brand'].queryset.filter(tenant=self._tenant)

    def clean(self):
        cleaned_data = super().clean()
        cost_price = cleaned_data.get('cost_price')
        selling_price = cleaned_data.get('selling_price')
        if cost_price is not None and selling_price is not None and selling_price < cost_price:
            raise forms.ValidationError('O preço de venda não pode ser inferior ao preço de custo.')
        return cleaned_data

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity is not None and quantity <= 0:
            raise forms.ValidationError('A quantidade deve ser maior que zero.')
        return quantity

    def clean_serial_number(self):
        serial_number = self.cleaned_data.get('serial_number')
        if not serial_number:
            return serial_number
        tenant_id = getattr(self._tenant, 'pk', None) or self.instance.tenant_id
        if tenant_id and models.Product.objects.filter(
            tenant=tenant_id,
            serial_number=serial_number,
        ).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Já existe um produto com este número de série.')
        return serial_number
