import csv
import uuid
from decimal import Decimal
from io import BytesIO

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, PasswordChangeView, PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from django.db.models import Sum, F, Q
from django.db.models.functions import Coalesce
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView, ListView, UpdateView, DetailView
from xhtml2pdf import pisa

from .forms import CustomerLoginForm, CustomerProfileForm
from .models import CustomerAccess, PortalSessionLog, StatementShareToken
from accounts.models import CustomerAccountEntry
from outflows.models import Outflow, Delivery
from payments.models import Payment


def _log_session(access, request, action):
    PortalSessionLog.objects.create(
        access=access,
        ip_address=request.META.get('REMOTE_ADDR', ''),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        action=action,
    )


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
        _log_session(access, self.request, 'login')
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

    def get_access(self):
        return CustomerAccess.objects.select_related('customer').get(
            user=self.request.user, is_active=True, is_deleted=False,
        )

    def get_tenant_filter(self):
        customer = self.get_customer()
        return {'tenant': customer.tenant} if customer.tenant_id else {}


class PortalDashboardView(PortalRequiredMixin, TemplateView):
    template_name = 'portal/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.get_customer()
        tf = self.get_tenant_filter()
        cache_key = f'portal_dash_{customer.id}'

        entries = CustomerAccountEntry.objects.filter(customer=customer)
        totals = entries.aggregate(
            d=Coalesce(Sum('debit'), Decimal('0')),
            c=Coalesce(Sum('credit'), Decimal('0')),
        )
        total_d = totals['d'] or Decimal('0')
        total_c = totals['c'] or Decimal('0')

        balance_evolution = []
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT strftime('%Y-%m', date) AS month, "
                    "COALESCE(SUM(debit), 0) AS md, COALESCE(SUM(credit), 0) AS mc "
                    "FROM accounts_customeraccountentry "
                    "WHERE customer_id = %s "
                    "GROUP BY strftime('%Y-%m', date) "
                    "ORDER BY month",
                    [customer.pk],
                )
                running = Decimal('0')
                for row in cursor.fetchall():
                    month, md, mc = row
                    running += Decimal(str(mc)) - Decimal(str(md))
                    balance_evolution.append({
                        'month': month,
                        'balance': float(running),
                    })
        except Exception:
            balance_evolution = []

        context['customer'] = customer
        context['balance'] = total_c - total_d
        context['total_debit'] = total_d
        context['total_credit'] = total_c
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
        context['balance_evolution'] = balance_evolution
        return context


class PortalAccountStatementView(PortalRequiredMixin, ListView):
    template_name = 'portal/account_statement.html'
    context_object_name = 'entries'
    paginate_by = 20

    def get_queryset(self):
        customer = self.get_customer()
        qs = CustomerAccountEntry.objects.filter(
            customer=customer,
        ).select_related('outflow__product', 'payment')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(description__icontains=q) |
                Q(outflow__product__title__icontains=q) |
                Q(outflow__id__icontains=q)
            )
        date_from = self.request.GET.get('date_from', '').strip()
        date_to = self.request.GET.get('date_to', '').strip()
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        t = self.request.GET.get('type', '').strip()
        if t == 'debit':
            qs = qs.filter(debit__gt=0)
        elif t == 'credit':
            qs = qs.filter(credit__gt=0)
        return qs.order_by('-date')

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
        context['q'] = self.request.GET.get('q', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        context['type_filter'] = self.request.GET.get('type', '')
        return context


class PortalDeliveriesView(PortalRequiredMixin, ListView):
    template_name = 'portal/deliveries.html'
    context_object_name = 'deliveries'
    paginate_by = 20

    def get_queryset(self):
        customer = self.get_customer()
        qs = Delivery.objects.filter(
            outflow__customer=customer,
        ).select_related('outflow__product', 'driver')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(outflow__product__title__icontains=q) |
                Q(driver__name__icontains=q) |
                Q(destination__icontains=q)
            )
        status = self.request.GET.get('status', '').strip()
        if status == 'confirmed':
            qs = qs.filter(is_confirmed=True)
        elif status == 'pending':
            qs = qs.filter(is_confirmed=False)
        return qs.order_by('-delivered_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer'] = self.get_customer()
        context['q'] = self.request.GET.get('q', '')
        context['status_filter'] = self.request.GET.get('status', '')
        return context


class PortalPaymentsView(PortalRequiredMixin, ListView):
    template_name = 'portal/payments.html'
    context_object_name = 'payments'
    paginate_by = 20

    def get_queryset(self):
        customer = self.get_customer()
        qs = Payment.objects.filter(
            customer=customer, type='RECEIPT',
        )
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(description__icontains=q) |
                Q(payment_method__icontains=q) |
                Q(id__icontains=q)
            )
        method = self.request.GET.get('method', '').strip()
        if method:
            qs = qs.filter(payment_method=method)
        date_from = self.request.GET.get('date_from', '').strip()
        date_to = self.request.GET.get('date_to', '').strip()
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs.order_by('-date', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer'] = self.get_customer()
        context['q'] = self.request.GET.get('q', '')
        context['method_filter'] = self.request.GET.get('method', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        return context


class PortalOutflowDetailView(PortalRequiredMixin, DetailView):
    template_name = 'portal/outflow_detail.html'
    context_object_name = 'outflow'

    def get_queryset(self):
        customer = self.get_customer()
        return Outflow.objects.filter(
            customer=customer,
        ).select_related('product').prefetch_related(
            'deliveries__driver',
            'account_entries',
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer'] = self.get_customer()
        outflow = self.object
        context['deliveries'] = outflow.deliveries.filter(
            is_deleted=False,
        ).select_related('driver').order_by('-delivered_at')
        context['progress_pct'] = (
            float(outflow.quantity_delivered) / float(outflow.quantity) * 100
            if outflow.quantity > 0 else 0
        )
        return context


class PortalExportStatementView(PortalRequiredMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        customer = self.get_customer()
        fmt = request.GET.get('format', 'csv')
        qs = CustomerAccountEntry.objects.filter(
            customer=customer,
        ).select_related('outflow__product', 'payment').order_by('-date')

        if fmt == 'csv':
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = f'attachment; filename="extracto_{customer.id}_{timezone.now():%Y%m%d}.csv"'
            response.write('\ufeff')
            writer = csv.writer(response)
            writer.writerow(['Data', 'Descrição', 'Débito', 'Crédito'])
            for e in qs:
                writer.writerow([
                    e.date.strftime('%d/%m/%Y %H:%M'),
                    e.description,
                    f'{e.debit:.2f}' if e.debit > 0 else '',
                    f'{e.credit:.2f}' if e.credit > 0 else '',
                ])
            return response

        return redirect('portal:account_statement')


class PortalExportStatementPDFView(PortalRequiredMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        customer = self.get_customer()
        qs = CustomerAccountEntry.objects.filter(
            customer=customer,
        ).select_related('outflow__product', 'payment').order_by('-date')

        totals = qs.aggregate(
            d=Coalesce(Sum('debit'), Decimal('0')),
            c=Coalesce(Sum('credit'), Decimal('0')),
        )

        html_string = render_to_string('portal/statement_pdf.html', {
            'customer': customer,
            'entries': qs,
            'total_debit': totals['d'],
            'total_credit': totals['c'],
            'balance': totals['c'] - totals['d'],
            'generated_at': timezone.now(),
            'company': settings.COMPANY_INFO,
        })

        result = BytesIO()
        pisa_status = pisa.CreatePDF(html_string, dest=result)
        if pisa_status.err:
            messages.error(request, 'Erro ao gerar PDF.')
            return redirect('portal:account_statement')

        result.seek(0)
        response = HttpResponse(result, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="extracto_{customer.name}_{timezone.now():%Y%m%d}.pdf"'
        )
        return response


class PortalShareStatementView(PortalRequiredMixin, TemplateView):
    template_name = 'portal/share_modal.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.get_customer()
        access = self.get_access()
        token, created = StatementShareToken.objects.get_or_create(
            access=access,
            defaults={'token': uuid.uuid4().hex[:16]},
        )
        share_url = self.request.build_absolute_uri(
            reverse('portal:shared_statement', kwargs={'token': token.token})
        )
        context.update({
            'share_url': share_url,
            'customer': customer,
        })
        return context


class PortalSharedStatementView(TemplateView):
    template_name = 'portal/share_statement.html'

    def get(self, request, *args, **kwargs):
        token = kwargs.get('token')
        share_token = get_object_or_404(
            StatementShareToken.objects.select_related('access__customer'),
            token=token, is_active=True,
        )
        if share_token.is_expired():
            raise Http404('O link de partilha expirou.')

        customer = share_token.access.customer
        qs = CustomerAccountEntry.objects.filter(
            customer=customer,
        ).order_by('-date')

        totals = qs.aggregate(
            d=Coalesce(Sum('debit'), Decimal('0')),
            c=Coalesce(Sum('credit'), Decimal('0')),
        )

        context = self.get_context_data(**kwargs)
        context.update({
            'customer': customer,
            'entries': qs,
            'total_debit': totals['d'],
            'total_credit': totals['c'],
            'balance': totals['c'] - totals['d'],
            'generated_at': timezone.now(),
        })
        return self.render_to_response(context)


class PortalPasswordChangeView(PortalRequiredMixin, PasswordChangeView):
    template_name = 'portal/password_change.html'
    success_url = reverse_lazy('portal:dashboard')

    def form_valid(self, form):
        messages.success(self.request, 'Palavra-passe alterada com sucesso!')
        access = self.get_access()
        _log_session(access, self.request, 'password_change')
        return super().form_valid(form)


class PortalProfileEditView(PortalRequiredMixin, UpdateView):
    template_name = 'portal/profile_edit.html'
    form_class = CustomerProfileForm

    def get_object(self, queryset=None):
        return self.get_customer()

    def get_success_url(self):
        return reverse('portal:profile_edit')

    def form_valid(self, form):
        messages.success(self.request, 'Perfil actualizado com sucesso!')
        return super().form_valid(form)


class PortalPasswordResetView(PasswordResetView):
    template_name = 'portal/password_reset.html'
    email_template_name = 'portal/password_reset_email.html'
    subject_template_name = 'portal/password_reset_subject.txt'
    success_url = reverse_lazy('portal:password_reset_done')

    def form_valid(self, form):
        messages.success(self.request, 'Se o email existir, receberá instruções para redefinir a palavra-passe.')
        return super().form_valid(form)


class PortalPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'portal/password_reset_done.html'


class PortalPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'portal/password_reset_confirm.html'
    success_url = reverse_lazy('portal:password_reset_complete')

    def form_valid(self, form):
        messages.success(self.request, 'Palavra-passe redefinida com sucesso!')
        return super().form_valid(form)


class PortalPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'portal/password_reset_complete.html'


class PortalSessionLogView(PortalRequiredMixin, ListView):
    template_name = 'portal/session_log.html'
    context_object_name = 'logs'
    paginate_by = 20

    def get_queryset(self):
        access = self.get_access()
        return PortalSessionLog.objects.filter(access=access).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer'] = self.get_customer()
        return context


