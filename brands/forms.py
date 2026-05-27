from django import forms
from django.db import IntegrityError
from . import models


class BrandForm(forms.ModelForm):
    class Meta:
        model = models.Brand
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'name': 'Nome',
            'description': 'Descrição',
        }

    def save(self, commit=True):
        try:
            return super().save(commit=commit)
        except IntegrityError:
            raise forms.ValidationError({'name': 'Já existe uma marca com este nome para esta empresa.'})