from django.contrib import admin
from . import models


class DeliveryInline(admin.TabularInline):
    model = models.Delivery
    extra = 0
    readonly_fields = ('delivered_at',)


class OutflowAdmin(admin.ModelAdmin):
    list_display = ('product', 'customer', 'quantity', 'quantity_delivered', 'status', 'created_at')
    list_filter = ('customer',)
    search_fields = ('product__title', 'customer__name')
    inlines = [DeliveryInline]
    readonly_fields = ('quantity_delivered',)


admin.site.register(models.Outflow, OutflowAdmin)
admin.site.register(models.Delivery)
