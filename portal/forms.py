from django import forms
from django.contrib.auth.forms import AuthenticationForm


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
