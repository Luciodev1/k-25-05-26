from django.contrib import admin
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.html import format_html
from django import forms
from .models import CustomerAccess
from customers.models import Customer


class CustomerAccessForm(forms.ModelForm):
    username = forms.CharField(
        max_length=150, label='Utilizador',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    password = forms.CharField(
        required=False, label='Palavra-passe',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='Deixar em branco para manter a actual (apenas na edição)',
    )

    class Meta:
        model = CustomerAccess
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['username'].initial = self.instance.user.username

    def clean_username(self):
        username = self.cleaned_data['username']
        if self.instance and self.instance.pk:
            if User.objects.exclude(pk=self.instance.user_id).filter(username=username).exists():
                raise forms.ValidationError('Este nome de utilizador já está em uso.')
        else:
            if User.objects.filter(username=username).exists():
                raise forms.ValidationError('Este nome de utilizador já está em uso.')
        return username

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
                password=self.cleaned_data['password'] or User.objects.make_random_password(),
            )
            instance.user = user
        if commit:
            instance.save()
        return instance


@admin.register(CustomerAccess)
class CustomerAccessAdmin(admin.ModelAdmin):
    form = CustomerAccessForm
    list_display = ('customer', 'user_link', 'is_active', 'last_login', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('customer__name', 'user__username')
    ordering = ('-created_at',)

    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user_id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'Utilizador'

    fieldsets = (
        ('Cliente', {'fields': ('customer',)}),
        ('Acesso', {'fields': ('username', 'password', 'is_active')}),
    )
