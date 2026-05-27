from django.shortcuts import get_object_or_404
from django.views.generic import ListView, CreateView
from django.db.models import Sum, F
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from app.mixins import FinanceiroRequiredMixin
from payments.models import Payment
from . import models, forms
from .filters import CustomerAccountFilter, SupplierAccountFilter


class CustomerAccountListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = models.CustomerAccountEntry
    template_name = 'customer_account.html'
    context_object_name = 'entries'
    paginate_by = 20
    permission_required = 'payments.view_payment'

    def get_queryset(self):
        qs = super().get_queryset().filter(
            customer_id=self.kwargs['pk']
        ).select_related('outflow__product', 'payment')
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        self.filterset = CustomerAccountFilter(self.request.GET, queryset=qs)
        self.full_qs = self.filterset.qs
        return self.full_qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from customers.models import Customer
        c_qs = Customer.objects
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            c_qs = c_qs.filter(tenant=tenant)
        customer = get_object_or_404(c_qs, pk=self.kwargs['pk'])
        totals = self.full_qs.aggregate(
            total_debit=Sum('debit'), total_credit=Sum('credit'),
        )
        context['customer'] = customer
        context['total_debit'] = totals['total_debit'] or 0
        context['total_credit'] = totals['total_credit'] or 0
        context['balance'] = (totals['total_credit'] or 0) - (totals['total_debit'] or 0)
        return context


class CustomerPaymentCreateView(FinanceiroRequiredMixin, CreateView):
    model = Payment
    template_name = 'customer_payment.html'
    form_class = forms.CustomerPaymentForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = getattr(self.request, 'tenant', None)
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        from customers.models import Customer
        from django.utils import timezone
        c_qs = Customer.objects
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            c_qs = c_qs.filter(tenant=tenant)
        customer = get_object_or_404(c_qs, pk=self.kwargs.get('pk'))
        initial['customer'] = customer
        initial['type'] = 'RECEIPT'
        initial['date'] = timezone.localdate()
        return initial

    def form_valid(self, form):
        form.instance.type = 'RECEIPT'
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            form.instance.tenant = tenant
        return super().form_valid(form)

    def get_success_url(self):
        from django.urls import reverse
        return reverse('accounts:customer_account', kwargs={'pk': self.object.customer.pk})


class SupplierAccountListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = models.SupplierAccountEntry
    template_name = 'supplier_account.html'
    context_object_name = 'entries'
    paginate_by = 20
    permission_required = 'payments.view_payment'

    def get_queryset(self):
        qs = super().get_queryset().filter(
            supplier_id=self.kwargs['pk']
        ).select_related('inflow__product', 'payment')
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        self.filterset = SupplierAccountFilter(self.request.GET, queryset=qs)
        self.full_qs = self.filterset.qs
        return self.full_qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from suppliers.models import Supplier
        s_qs = Supplier.objects
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            s_qs = s_qs.filter(tenant=tenant)
        supplier = get_object_or_404(s_qs, pk=self.kwargs['pk'])
        totals = self.full_qs.aggregate(
            total_debit=Sum('debit'), total_credit=Sum('credit'),
        )
        context['supplier'] = supplier
        context['total_debit'] = totals['total_debit'] or 0
        context['total_credit'] = totals['total_credit'] or 0
        context['balance'] = (totals['total_debit'] or 0) - (totals['total_credit'] or 0)
        return context


class SupplierPaymentCreateView(FinanceiroRequiredMixin, CreateView):
    model = Payment
    template_name = 'supplier_payment.html'
    form_class = forms.SupplierPaymentForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = getattr(self.request, 'tenant', None)
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        from suppliers.models import Supplier
        from django.utils import timezone
        s_qs = Supplier.objects
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            s_qs = s_qs.filter(tenant=tenant)
        supplier = get_object_or_404(s_qs, pk=self.kwargs.get('pk'))
        initial['supplier'] = supplier
        initial['type'] = 'PAYMENT'
        initial['date'] = timezone.localdate()
        return initial

    def form_valid(self, form):
        form.instance.type = 'PAYMENT'
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            form.instance.tenant = tenant
        return super().form_valid(form)

    def get_success_url(self):
        from django.urls import reverse
        return reverse('accounts:supplier_account', kwargs={'pk': self.object.supplier.pk})



class CustomerBalanceListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    template_name = 'customer_balances.html'
    context_object_name = 'customers'
    permission_required = 'payments.view_payment'

    def get_queryset(self):
        from customers.models import Customer
        qs = Customer.objects
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs.annotate(
            total_debit=Sum('account_entries__debit', default=0),
            total_credit=Sum('account_entries__credit', default=0),
            balance=F('total_credit') - F('total_debit'),
        ).order_by('name')


class SupplierBalanceListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    template_name = 'supplier_balances.html'
    context_object_name = 'suppliers'
    permission_required = 'payments.view_payment'

    def get_queryset(self):
        from suppliers.models import Supplier
        qs = Supplier.objects
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs.annotate(
            total_debit=Sum('account_entries__debit', default=0),
            total_credit=Sum('account_entries__credit', default=0),
            balance=F('total_debit') - F('total_credit'),
        ).order_by('name')
