from django.contrib import admin
from . import models


class InflowAdmin(admin.ModelAdmin):
    list_display = ('product', 'supplier', 'quantity', 'created_at')
    list_filter = ('supplier',)
    search_fields = ('product__title', 'supplier__name')
    list_select_related = ('product', 'supplier')


admin.site.register(models.Inflow, InflowAdmin)
