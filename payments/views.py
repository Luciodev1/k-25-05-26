from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.views import View
from django.shortcuts import redirect
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django_filters.views import FilterView
from app.mixins import HtmxMixin
from .models import Payment
from .forms import PaymentForm
from .filters import PaymentFilter


class PaymentListView(LoginRequiredMixin, PermissionRequiredMixin, HtmxMixin, FilterView):
    model = Payment
    template_name = 'payment_list.html'
    htmx_template_name = 'payment_list_partial.html'
    context_object_name = 'payments'
    permission_required = 'payments.view_payment'
    paginate_by = 15
    filterset_class = PaymentFilter

    def get_queryset(self):
        qs = super().get_queryset().select_related('customer', 'supplier')
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        self.filterset = self.filterset_class(self.request.GET, queryset=qs)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['type_filter'] = self.request.GET.get('type', '')
        context['method_filter'] = self.request.GET.get('method', '')
        context['type_choices'] = Payment.TYPE_CHOICES
        context['method_choices'] = Payment.METHOD_CHOICES
        return context


class PaymentDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Payment
    template_name = 'payment_detail.html'
    context_object_name = 'payment'
    permission_required = 'payments.view_payment'

    def get_queryset(self):
        qs = super().get_queryset().select_related('customer', 'supplier')
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs


class PaymentCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'payment_create.html'
    success_url = reverse_lazy('payments:payment_list')
    success_message = "Pagamento registado com sucesso!"
    permission_required = 'payments.add_payment'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = getattr(self.request, 'tenant', None)
        return kwargs

    def form_valid(self, form):
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            form.instance.tenant = tenant
        return super().form_valid(form)


class PaymentUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'payment_update.html'
    success_url = reverse_lazy('payments:payment_list')
    success_message = "Pagamento atualizado com sucesso!"
    permission_required = 'payments.change_payment'

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


class PaymentDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Payment
    template_name = 'payment_delete.html'
    success_url = reverse_lazy('payments:payment_list')
    permission_required = 'payments.delete_payment'

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
            messages.success(request, "Pagamento eliminado com sucesso!")
            return redirect(self.success_url)
        except ProtectedError:
            messages.error(request, "Nao e possivel eliminar este pagamento porque esta a ser utilizado por outros registos.")
            return redirect(self.success_url)


class PaymentTrashListView(LoginRequiredMixin, PermissionRequiredMixin, HtmxMixin, ListView):
    model = Payment
    template_name = 'payment_trash.html'
    htmx_template_name = 'payment_trash_partial.html'
    context_object_name = 'payments'
    permission_required = 'payments.delete_payment'
    paginate_by = 15

    def get_queryset(self):
        qs = Payment.all_objects.filter(is_deleted=True).select_related('customer', 'supplier')
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs


class PaymentRestoreView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'payments.delete_payment'

    def post(self, request, pk):
        qs = Payment.all_objects
        tenant = getattr(request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        payment = qs.get(pk=pk)
        payment.restore()
        messages.success(request, "Pagamento restaurado com sucesso!")
        return redirect('payments:payment_trash')


class PaymentHardDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'payments.delete_payment'

    def post(self, request, pk):
        from django.db.models import ProtectedError
        try:
            qs = Payment.all_objects
            tenant = getattr(request, 'tenant', None)
            if tenant:
                qs = qs.filter(tenant=tenant)
            payment = qs.get(pk=pk)
            payment.hard_delete()
            messages.success(request, "Pagamento eliminado permanentemente!")
        except ProtectedError:
            messages.error(request, "Nao e possivel eliminar permanentemente este pagamento.")
        return redirect('payments:payment_trash')
