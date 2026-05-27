from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, TemplateView
from django_filters.views import FilterView
from .models import AuditLog
from .filters import AuditLogFilter


class AuditLogListView(LoginRequiredMixin, PermissionRequiredMixin, FilterView):
    model = AuditLog
    template_name = 'audit_list.html'
    context_object_name = 'logs'
    paginate_by = 50
    permission_required = 'audit.view_auditlog'
    raise_exception = True
    filterset_class = AuditLogFilter

    def get_queryset(self):
        qs = super().get_queryset().select_related('user')
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        self.filterset = self.filterset_class(self.request.GET, queryset=qs)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = getattr(self.request, 'tenant', None)
        context['action_choices'] = AuditLog.ACTION_CHOICES
        base_models = AuditLog.objects
        if tenant:
            base_models = base_models.filter(tenant=tenant)
        context['model_choices'] = base_models.values_list('model_name', flat=True).distinct()
        context['action_filter'] = self.request.GET.get('action', '')
        context['model_filter'] = self.request.GET.get('model', '')
        return context


class ActivityFeedView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'activity_feed.html'
    permission_required = 'audit.view_auditlog'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = AuditLog.objects.select_related('user')
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        context['recent_activities'] = qs.order_by('-timestamp')[:50]
        return context

