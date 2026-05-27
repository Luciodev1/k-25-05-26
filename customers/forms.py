import re
from django import forms
from . import models


class CustomerForm(forms.ModelForm):

    class Meta:
        model = models.Customer
        fields = ['name', 'phone', 'nif', 'address', 'email']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+244 9XX XXX XXX'}),
            'nif': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'XXXXXXXXXX'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'exemplo@email.com'}),
        }
        labels = {
            'name': 'Nome',
            'phone': 'Telefone',
            'nif': 'NIF',
            'address': 'Morada',
            'email': 'Email',
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            cleaned = re.sub(r'[\s\-\(\)]', '', phone)
            if not re.match(r'^\+?\d{9,15}$', cleaned):
                raise forms.ValidationError('Formato de telefone invalido. Use: +244 9XX XXX XXX')
        return phone

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
            raise forms.ValidationError({'nif': 'Já existe um cliente com este NIF.'})
