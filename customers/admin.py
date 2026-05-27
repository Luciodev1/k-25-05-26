from django.contrib import admin
from . import models


class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'nif', 'email')
    search_fields = ('name', 'nif', 'email')


admin.site.register(models.Customer, CustomerAdmin)
