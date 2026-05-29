from django.db import transaction
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.views import View
from django.shortcuts import redirect
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django_filters.views import FilterView
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from products.models import Product
from app.mixins import HtmxMixin
from . import models, forms
from .filters import InflowFilter


class InflowListView(LoginRequiredMixin, PermissionRequiredMixin, HtmxMixin, FilterView):
    model = models.Inflow
    template_name = 'inflow_list.html'
    htmx_template_name = 'inflow_list_partial.html'
    context_object_name = 'inflows'
    permission_required = 'inflows.view_inflow'
    paginate_by = 10
    filterset_class = InflowFilter

    def get_queryset(self):
        qs = super().get_queryset().select_related('product', 'supplier')
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        self.filterset = self.filterset_class(self.request.GET, queryset=qs)
        return self.filterset.qs


@method_decorator(ratelimit(key='user_or_ip', rate='30/m', method='POST', block=True), name='dispatch')
class InflowCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = models.Inflow
    template_name = 'inflow_create.html'
    form_class = forms.InflowForm
    success_url = reverse_lazy('inflows:inflow_list')
    permission_required = 'inflows.add_inflow'
    success_message = "Entrada registada com sucesso!"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = getattr(self.request, 'tenant', None)
        return kwargs

    def form_valid(self, form):
        try:
            with transaction.atomic():
                qs = Product.objects
                tenant = getattr(self.request, 'tenant', None)
                if tenant:
                    qs = qs.filter(tenant=tenant)
                product = qs.select_for_update().get(
                    pk=form.cleaned_data['product'].pk
                )
                inflow = form.save(commit=False)
                tenant = getattr(self.request, 'tenant', None)
                if tenant:
                    inflow.tenant = tenant
                if not inflow.price:
                    inflow.price = product.cost_price
                inflow.save()
        except Product.DoesNotExist:
            form.add_error('product', 'O produto selecionado já não existe.')
            return self.form_invalid(form)
        return super().form_valid(form)


@method_decorator(ratelimit(key='user_or_ip', rate='30/m', method='POST', block=True), name='dispatch')
class InflowUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = models.Inflow
    template_name = 'inflow_update.html'
    form_class = forms.InflowForm
    success_url = reverse_lazy('inflows:inflow_list')
    permission_required = 'inflows.change_inflow'
    success_message = "Entrada atualizada com sucesso!"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = getattr(self.request, 'tenant', None)
        return kwargs

    def get_queryset(self):
        qs = super().get_queryset()
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs


class InflowDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = models.Inflow
    template_name = 'inflow_detail.html'
    context_object_name = 'inflow'
    permission_required = 'inflows.view_inflow'

    def get_queryset(self):
        qs = super().get_queryset().select_related('product', 'supplier')
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs


@method_decorator(ratelimit(key='user_or_ip', rate='20/m', method='POST', block=True), name='post')
class InflowDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = models.Inflow
    template_name = 'inflow_delete.html'
    success_url = reverse_lazy('inflows:inflow_list')
    permission_required = 'inflows.delete_inflow'

    def get_queryset(self):
        qs = super().get_queryset()
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs

    def post(self, request, *args, **kwargs):
        from django.db.models import ProtectedError
        try:
            obj = self.get_object()
            obj.delete()
            messages.success(request, "Entrada excluida com sucesso!")
            return redirect(self.success_url)
        except ProtectedError:
            messages.error(request, "Nao e possivel eliminar esta entrada porque esta a ser utilizada por outros registos.")
            return redirect(self.success_url)


class InflowTrashListView(LoginRequiredMixin, PermissionRequiredMixin, HtmxMixin, ListView):
    model = models.Inflow
    template_name = 'inflow_trash.html'
    htmx_template_name = 'inflow_trash_partial.html'
    context_object_name = 'inflows'
    permission_required = 'inflows.delete_inflow'
    paginate_by = 10

    def get_queryset(self):
        qs = models.Inflow.all_objects.filter(is_deleted=True).select_related('product', 'supplier')
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs


@method_decorator(ratelimit(key='user_or_ip', rate='15/m', method='POST', block=True), name='post')
class InflowRestoreView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'inflows.delete_inflow'

    def post(self, request, pk):
        qs = models.Inflow.all_objects
        tenant = getattr(request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        inflow = qs.get(pk=pk)
        inflow.restore()
        messages.success(request, "Entrada restaurada com sucesso!")
        return redirect('inflows:inflow_trash')


@method_decorator(ratelimit(key='user_or_ip', rate='10/m', method='POST', block=True), name='post')
class InflowHardDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'inflows.delete_inflow'

    def post(self, request, pk):
        from django.db.models import ProtectedError
        try:
            qs = models.Inflow.all_objects
            tenant = getattr(request, 'tenant', None)
            if tenant:
                qs = qs.filter(tenant=tenant)
            inflow = qs.get(pk=pk)
            inflow.hard_delete()
            messages.success(request, "Entrada eliminada permanentemente!")
        except ProtectedError:
            messages.error(request, "Nao e possivel eliminar permanentemente esta entrada.")
        return redirect('inflows:inflow_trash')
