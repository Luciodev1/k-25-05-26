from django import forms
from django.contrib.auth.models import User
from customers.models import Customer
from portal.models import CustomerAccess


class PortalAccessForm(forms.ModelForm):
    username = forms.CharField(
        max_length=150, label='Utilizador',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome de utilizador para login'}),
    )
    password = forms.CharField(
        required=False, label='Palavra-passe',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Deixar em branco para manter'}),
        help_text='Mínimo 8 caracteres. Deixar em branco para manter a actual (apenas na edição).',
    )

    class Meta:
        model = CustomerAccess
        fields = ['customer', 'is_active']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'customer': 'Cliente',
            'is_active': 'Acesso Activo',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['customer'].queryset = Customer.all_objects.order_by('name')
        if self.instance and self.instance.pk:
            self.fields['username'].initial = self.instance.user.username
            self.fields['username'].help_text = 'Alterar o nome de utilizador'
            self.fields['password'].required = False
        else:
            self.fields['password'].required = True
            self.fields['password'].help_text = 'Mínimo 8 caracteres.'

    def clean_username(self):
        username = self.cleaned_data['username']
        if self.instance and self.instance.pk:
            if User.objects.exclude(pk=self.instance.user_id).filter(username=username).exists():
                raise forms.ValidationError('Este nome de utilizador já está em uso.')
        else:
            if User.objects.filter(username=username).exists():
                raise forms.ValidationError('Este nome de utilizador já está em uso.')
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password and len(password) < 8:
            raise forms.ValidationError('A palavra-passe deve ter pelo menos 8 caracteres.')
        return password

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.pk:
            user = instance.user
            user.username = self.cleaned_data['username']
            if self.cleaned_data['password']:
                user.set_password(self.cleaned_data['password'])
            if commit:
                user.save()
        else:
            user = User.objects.create_user(
                username=self.cleaned_data['username'],
                password=self.cleaned_data['password'],
            )
            instance.user = user
        if commit:
            instance.save()
        return instance
