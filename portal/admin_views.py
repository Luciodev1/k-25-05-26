from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.db import models
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from portal.models import CustomerAccess
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
        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total'] = CustomerAccess.objects.count()
        context['active'] = CustomerAccess.objects.filter(is_active=True).count()
        return context


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
