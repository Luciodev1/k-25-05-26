from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.db import models
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View
from portal.models import CustomerAccess, PortalSessionLog
from portal.admin_forms import PortalAccessForm


class PortalAccessRequiredMixin(LoginRequiredMixin, PermissionRequiredMixin):
    permission_required = 'portal.view_customeraccess'

    def handle_no_permission(self):
        messages.error(self.request, 'Não tem permissão para gerir acessos ao portal.')
        return redirect('dashboard')


class PortalAccessListView(PortalAccessRequiredMixin, ListView):
    model = CustomerAccess
    template_name = 'portal/access_list.html'
    context_object_name = 'accesses'
    paginate_by = 20
    permission_required = 'portal.view_customeraccess'

    def get_queryset(self):
        qs = super().get_queryset().select_related('user', 'customer')
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                models.Q(customer__name__icontains=q) |
                models.Q(user__username__icontains=q)
            )
        status = self.request.GET.get('status', '').strip()
        if status == 'active':
            qs = qs.filter(is_active=True)
        elif status == 'inactive':
            qs = qs.filter(is_active=False)
        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total'] = CustomerAccess.objects.count()
        context['active'] = CustomerAccess.objects.filter(is_active=True).count()
        context['status_filter'] = self.request.GET.get('status', '')
        context['q'] = self.request.GET.get('q', '')
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('bulk_action')
        ids = request.POST.getlist('selected_ids')
        if not ids:
            messages.warning(request, 'Seleccione pelo menos um acesso.')
            return redirect('portal_acessos:list')

        if action == 'activate':
            count = CustomerAccess.objects.filter(id__in=ids, is_active=False).update(is_active=True)
            messages.success(request, f'{count} acesso(s) activado(s) com sucesso.')
        elif action == 'deactivate':
            count = CustomerAccess.objects.filter(id__in=ids, is_active=True).update(is_active=False)
            messages.success(request, f'{count} acesso(s) desactivado(s) com sucesso.')
        return redirect('portal_acessos:list')


class PortalAccessCreateView(PortalAccessRequiredMixin, CreateView):
    model = CustomerAccess
    template_name = 'portal/access_form.html'
    form_class = PortalAccessForm
    permission_required = 'portal.add_customeraccess'
    success_message = 'Acesso ao portal criado com sucesso!'

    def get_success_url(self):
        return reverse('portal_acessos:list')

    def form_valid(self, form):
        messages.success(self.request, self.success_message)
        return super().form_valid(form)


class PortalAccessUpdateView(PortalAccessRequiredMixin, UpdateView):
    model = CustomerAccess
    template_name = 'portal/access_form.html'
    form_class = PortalAccessForm
    permission_required = 'portal.change_customeraccess'
    success_message = 'Acesso ao portal actualizado com sucesso!'

    def get_success_url(self):
        return reverse('portal_acessos:list')

    def form_valid(self, form):
        messages.success(self.request, self.success_message)
        return super().form_valid(form)


class PortalAccessDetailView(PortalAccessRequiredMixin, DetailView):
    model = CustomerAccess
    template_name = 'portal/access_detail.html'
    context_object_name = 'access'
    permission_required = 'portal.view_customeraccess'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['session_logs'] = PortalSessionLog.objects.filter(
            access=self.object,
        ).order_by('-created_at')[:20]
        return context


class PortalAccessDeleteView(PortalAccessRequiredMixin, DeleteView):
    model = CustomerAccess
    template_name = 'portal/access_confirm_delete.html'
    permission_required = 'portal.delete_customeraccess'
    success_message = 'Acesso ao portal removido com sucesso!'

    def get_success_url(self):
        return reverse('portal_acessos:list')

    def form_valid(self, form):
        messages.success(self.request, self.success_message)
        return super().form_valid(form)


class PortalSessionLogAdminView(PortalAccessRequiredMixin, ListView):
    model = PortalSessionLog
    template_name = 'portal/admin_session_logs.html'
    context_object_name = 'logs'
    paginate_by = 30
    permission_required = 'portal.view_customeraccess'

    def get_queryset(self):
        qs = super().get_queryset().select_related('access__customer', 'access__user')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                models.Q(access__customer__name__icontains=q) |
                models.Q(access__user__username__icontains=q) |
                models.Q(ip_address__icontains=q)
            )
        action = self.request.GET.get('action', '').strip()
        if action:
            qs = qs.filter(action=action)
        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        context['action_filter'] = self.request.GET.get('action', '')
        return context
