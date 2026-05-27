from django.contrib import admin
from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'email_notifications', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone']
    list_filter = ['email_notifications']
