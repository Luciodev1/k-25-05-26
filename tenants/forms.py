from django import forms
from django.contrib.auth.models import User
from .models import Tenant, TenantUser


class TenantUserAddForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('username'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Utilizador',
    )
    role = forms.ChoiceField(
        choices=TenantUser.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Função',
        initial='operator',
    )

    def __init__(self, tenant=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant:
            existing_ids = TenantUser.objects.filter(tenant=tenant).values_list('user_id', flat=True)
            self.fields['user'].queryset = User.objects.filter(
                is_active=True,
            ).exclude(id__in=existing_ids).order_by('username')


class TenantCreateForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = ['name', 'slug', 'description', 'currency', 'timezone', 'language', 'max_users']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da Empresa'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'slug-da-empresa'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descrição opcional'}),
            'currency': forms.TextInput(attrs={'class': 'form-control', 'value': 'AOA'}),
            'timezone': forms.TextInput(attrs={'class': 'form-control', 'value': 'Africa/Luanda'}),
            'language': forms.TextInput(attrs={'class': 'form-control', 'value': 'pt-pt'}),
            'max_users': forms.NumberInput(attrs={'class': 'form-control', 'value': 10}),
        }
        labels = {
            'name': 'Nome',
            'slug': 'Slug (URL)',
            'description': 'Descrição',
            'currency': 'Moeda',
            'timezone': 'Fuso Horário',
            'language': 'Idioma',
            'max_users': 'Máx. Utilizadores',
        }
