from django.contrib import admin
from app.mixins import BulkDeleteMixin
from . import models


class ProductAdmin(BulkDeleteMixin, admin.ModelAdmin):
    list_display = ('title', 'category', 'brand', 'quantity', 'cost_price', 'selling_price')
    list_filter = ('category', 'brand')
    search_fields = ('title', 'serial_number')


admin.site.register(models.Product, ProductAdmin)
