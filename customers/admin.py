from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from . import models
from portal.models import CustomerAccess


class CustomerAccessInline(admin.TabularInline):
    model = CustomerAccess
    extra = 0
    fields = ('user_link', 'is_active', 'last_login')
    readonly_fields = ('user_link', 'last_login')
    can_delete = True
    verbose_name = 'Acesso ao Portal'
    verbose_name_plural = 'Acessos ao Portal'

    def user_link(self, obj):
        if obj.pk:
            url = reverse('admin:auth_user_change', args=[obj.user_id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return '-'
    user_link.short_description = 'Utilizador'

    def has_add_permission(self, request, obj=None):
        return False


class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'nif', 'email')
    search_fields = ('name', 'nif', 'email')
    inlines = [CustomerAccessInline]


admin.site.register(models.Customer, CustomerAdmin)
