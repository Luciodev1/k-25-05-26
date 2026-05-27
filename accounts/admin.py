from django.contrib import admin
from . import models


class CustomerAccountEntryAdmin(admin.ModelAdmin):
    list_display = ('customer', 'date', 'description', 'debit', 'credit')
    list_filter = ('customer',)
    search_fields = ('customer__name', 'description')


class SupplierAccountEntryAdmin(admin.ModelAdmin):
    list_display = ('supplier', 'date', 'description', 'debit', 'credit')
    list_filter = ('supplier',)
    search_fields = ('supplier__name', 'description')


admin.site.register(models.CustomerAccountEntry, CustomerAccountEntryAdmin)
admin.site.register(models.SupplierAccountEntry, SupplierAccountEntryAdmin)
