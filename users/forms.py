from django import forms
from django.contrib.auth.models import User, Group
from django.contrib.auth import password_validation
from .models import Profile


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['avatar', 'phone', 'bio', 'email_notifications']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(+244) 923 000 000'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Fale um pouco sobre si...'}),
            'email_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'avatar': 'Foto de Perfil',
            'phone': 'Telefone',
            'bio': 'Biografia',
            'email_notifications': 'Receber notificações por e-mail',
        }


class UserInfoForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apelido'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@exemplo.com'}),
        }
        labels = {
            'first_name': 'Nome',
            'last_name': 'Apelido',
            'email': 'E-mail',
        }


class UserCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Senha")
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Grupos / Permissões"
    )
    tenant_role = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Função na Empresa",
        required=False,
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password', 'is_active', 'is_staff', 'groups']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.tenant = kwargs.pop('tenant', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        if self.tenant:
            from tenants.models import TenantUser
            self.fields['tenant_role'].choices = TenantUser.ROLE_CHOICES
            self.fields['tenant_role'].initial = 'operator'
            if self.request:
                current_tu = TenantUser.objects.filter(user=self.request.user, tenant=self.tenant).first()
                if not current_tu or current_tu.role != 'admin':
                    self.fields['tenant_role'].choices = [
                        c for c in TenantUser.ROLE_CHOICES if c[0] != 'admin'
                    ]
        else:
            self.fields['tenant_role'].widget = forms.HiddenInput()

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            password_validation.validate_password(password, self.instance)
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            self.save_m2m()
        return user


class UserUpdateForm(forms.ModelForm):
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Grupos / Permissões"
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'groups']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
