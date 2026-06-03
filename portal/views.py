from django.contrib.auth import login
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, F, Q
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView, ListView
from django.contrib import messages
from decimal import Decimal

from .forms import CustomerLoginForm
from .models import CustomerAccess
from accounts.models import CustomerAccountEntry
from outflows.models import Outflow, Delivery
from payments.models import Payment


class CustomerLoginView(LoginView):
    template_name = 'portal/login.html'
    authentication_form = CustomerLoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse('portal:dashboard')

    def form_valid(self, form):
        user = form.get_user()
        try:
            access = CustomerAccess.objects.select_related('customer').get(
                user=user, is_active=True, is_deleted=False,
            )
            access.last_login = timezone.now()
            access.save(update_fields=['last_login'])
        except CustomerAccess.DoesNotExist:
            messages.error(self.request, 'Não tem acesso ao portal de cliente.')
            return self.form_invalid(form)
        login(self.request, user)
        return super().form_valid(form)


class PortalRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not CustomerAccess.objects.filter(
            user=request.user, is_active=True, is_deleted=False,
        ).exists():
            messages.error(request, 'Acesso não autorizado.')
            return redirect('portal:login')
        return super().dispatch(request, *args, **kwargs)

    def get_customer(self):
        access = CustomerAccess.objects.select_related('customer').get(
            user=self.request.user, is_active=True, is_deleted=False,
        )
        return access.customer

    def get_tenant_filter(self):
        customer = self.get_customer()
        return {'tenant': customer.tenant} if customer.tenant_id else {}


class PortalDashboardView(PortalRequiredMixin, TemplateView):
    template_name = 'portal/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.get_customer()
        tf = self.get_tenant_filter()

        entries = CustomerAccountEntry.objects.filter(customer=customer)
        totals = entries.aggregate(
            d=Coalesce(Sum('debit'), Decimal('0')),
            c=Coalesce(Sum('credit'), Decimal('0')),
        )
        context['customer'] = customer
        context['balance'] = totals['c'] - totals['d']
        context['total_debit'] = totals['d']
        context['total_credit'] = totals['c']
        context['outflows_count'] = Outflow.objects.filter(customer=customer, **tf).count()
        context['recent_outflows'] = Outflow.objects.filter(
            customer=customer, **tf,
        ).select_related('product').order_by('-created_at')[:5]
        context['recent_payments'] = Payment.objects.filter(
            customer=customer, **tf,
        ).order_by('-date', '-created_at')[:5]
        context['pending_deliveries'] = Delivery.objects.filter(
            outflow__customer=customer, **tf,
        ).select_related('outflow__product', 'driver').filter(
            is_confirmed=False,
        ).order_by('-delivered_at')[:5]
        return context


class PortalAccountStatementView(PortalRequiredMixin, ListView):
    template_name = 'portal/account_statement.html'
    context_object_name = 'entries'
    paginate_by = 20

    def get_queryset(self):
        customer = self.get_customer()
        return CustomerAccountEntry.objects.filter(
            customer=customer,
        ).select_related('outflow__product', 'payment').order_by('-date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.get_customer()
        entries = CustomerAccountEntry.objects.filter(customer=customer)
        totals = entries.aggregate(
            d=Coalesce(Sum('debit'), Decimal('0')),
            c=Coalesce(Sum('credit'), Decimal('0')),
        )
        context['customer'] = customer
        context['balance'] = totals['c'] - totals['d']
        context['total_debit'] = totals['d']
        context['total_credit'] = totals['c']
        return context


class PortalDeliveriesView(PortalRequiredMixin, ListView):
    template_name = 'portal/deliveries.html'
    context_object_name = 'deliveries'
    paginate_by = 20

    def get_queryset(self):
        customer = self.get_customer()
        return Delivery.objects.filter(
            outflow__customer=customer,
        ).select_related('outflow__product', 'driver').order_by('-delivered_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer'] = self.get_customer()
        return context


class PortalPaymentsView(PortalRequiredMixin, ListView):
    template_name = 'portal/payments.html'
    context_object_name = 'payments'
    paginate_by = 20

    def get_queryset(self):
        customer = self.get_customer()
        return Payment.objects.filter(
            customer=customer, type='RECEIPT',
        ).order_by('-date', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer'] = self.get_customer()
        return context


class PortalPasswordChangeView(PortalRequiredMixin, PasswordChangeView):
    template_name = 'portal/password_change.html'
    success_url = reverse_lazy('portal:dashboard')

    def form_valid(self, form):
        messages.success(self.request, 'Palavra-passe alterada com sucesso!')
        return super().form_valid(form)
