from django import forms
from django.core.validators import RegexValidator
from .models import Driver

phone_validator = RegexValidator(
    regex=r'^\+?\d{9,15}$',
    message='Formato de telefone inválido. Use apenas dígitos e opcionalmente + no início.',
)
plate_validator = RegexValidator(
    regex=r'^[A-Za-z]{2}-\d{2}-[A-Za-z]{2}-\d{2}$',
    message='Formato de matrícula inválido. Use o formato: AA-00-AA-00.',
)


class DriverForm(forms.ModelForm):
    phone = forms.CharField(
        validators=[phone_validator],
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Telefone',
    )
    truck_plate = forms.CharField(
        validators=[plate_validator],
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Matrícula do Camião',
    )
    cistern_plate = forms.CharField(
        required=False,
        validators=[plate_validator],
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Matrícula da Cisterna',
    )

    class Meta:
        model = Driver
        fields = ['name', 'phone', 'truck_plate', 'cistern_plate']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'Nome',
        }
