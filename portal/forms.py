from django import forms
from django.contrib.auth.forms import AuthenticationForm

from customers.models import Customer


class CustomerProfileForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'phone', 'email', 'address']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome completo'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Telefone'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'seu@email.com'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Endereço', 'rows': 3}),
        }
        labels = {
            'name': 'Nome',
            'phone': 'Telefone',
            'email': 'Email',
            'address': 'Endereço',
        }


class CustomerLoginForm(AuthenticationForm):
    username = forms.CharField(
        label='NIF ou Email',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'O seu NIF ou email',
            'autocomplete': 'username',
        }),
    )
    password = forms.CharField(
        label='Palavra-passe',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'A sua palavra-passe',
            'autocomplete': 'current-password',
        }),
    )
