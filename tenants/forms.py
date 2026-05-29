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

    def __init__(self, tenant=None, current_user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant:
            existing_ids = TenantUser.objects.filter(tenant=tenant).values_list('user_id', flat=True)
            self.fields['user'].queryset = User.objects.filter(
                is_active=True,
            ).exclude(id__in=existing_ids).order_by('username')
            if current_user:
                current_tu = TenantUser.objects.filter(user=current_user, tenant=tenant).first()
                if not current_tu or current_tu.role != 'admin':
                    self.fields['role'].choices = [
                        c for c in TenantUser.ROLE_CHOICES if c[0] != 'admin'
                    ]


class TenantCreateForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = ['name', 'slug', 'description', 'nif', 'phone', 'email', 'address', 'currency', 'timezone', 'language', 'max_users']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da Empresa'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'slug-da-empresa'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descrição opcional'}),
            'nif': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'NIF da empresa'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Telefone'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@empresa.co.ao'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Endereço da empresa'}),
            'currency': forms.TextInput(attrs={'class': 'form-control', 'value': 'AOA'}),
            'timezone': forms.TextInput(attrs={'class': 'form-control', 'value': 'Africa/Luanda'}),
            'language': forms.TextInput(attrs={'class': 'form-control', 'value': 'pt-pt'}),
            'max_users': forms.NumberInput(attrs={'class': 'form-control', 'value': 10}),
        }
        labels = {
            'name': 'Nome',
            'slug': 'Slug (URL)',
            'description': 'Descrição',
            'nif': 'NIF',
            'phone': 'Telefone',
            'email': 'Email',
            'address': 'Endereço',
            'currency': 'Moeda',
            'timezone': 'Fuso Horário',
            'language': 'Idioma',
            'max_users': 'Máx. Utilizadores',
        }
