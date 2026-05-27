from django.contrib import admin
from . import models


@admin.register(models.Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'truck_plate', 'cistern_plate')
    search_fields = ('name', 'truck_plate')
