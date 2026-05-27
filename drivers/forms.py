from django import forms
from .models import Driver


class DriverForm(forms.ModelForm):
    class Meta:
        model = Driver
        fields = ['name', 'phone', 'truck_plate', 'cistern_plate']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'truck_plate': forms.TextInput(attrs={'class': 'form-control'}),
            'cistern_plate': forms.TextInput(attrs={'class': 'form-control'}),
        }
