from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['date', 'type', 'customer', 'supplier', 'amount', 'payment_method', 'created_at']
    list_filter = ['type', 'payment_method']
    search_fields = ['customer__name', 'supplier__name', 'description']
