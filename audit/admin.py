from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'action', 'model_name', 'object_repr', 'user')
    list_filter = ('action', 'model_name', 'timestamp')
    search_fields = ('object_repr', 'object_id')
    readonly_fields = ('user', 'action', 'model_name', 'object_id', 'object_repr', 'changes', 'timestamp')
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
