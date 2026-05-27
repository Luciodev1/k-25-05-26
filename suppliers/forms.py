from django import forms
from . import models


class SupplierForm(forms.ModelForm):

    class Meta:
        model = models.Supplier
        fields = ['name', 'description', 'nif', 'email']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'nif': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'XXXXXXXXX'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'Nome',
            'description': 'Descrição',
            'nif': 'NIF',
            'email': 'Email',
        }

    def clean_nif(self):
        from app.validators import validate_angolan_nif
        nif = self.cleaned_data.get('nif')
        if nif:
            validate_angolan_nif(nif)
        return nif

    def save(self, commit=True):
        from django.db import IntegrityError
        try:
            return super().save(commit=commit)
        except IntegrityError:
            raise forms.ValidationError({'nif': 'Já existe um fornecedor com este NIF.'})
