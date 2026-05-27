from django.contrib import admin
from .models import Tenant, TenantUser, TenantSettings


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'max_users', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(TenantUser)
class TenantUserAdmin(admin.ModelAdmin):
    list_display = ['user', 'tenant', 'role', 'is_primary', 'joined_at']
    list_filter = ['role', 'is_primary', 'tenant']
    search_fields = ['user__username', 'tenant__name']


@admin.register(TenantSettings)
class TenantSettingsAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'email_notifications', 'require_mfa', 'auto_generate_reports']
