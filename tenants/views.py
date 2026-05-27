import logging
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, DetailView, View
from .models import Tenant, TenantUser, TenantSettings
from .forms import TenantCreateForm, TenantUserAddForm

logger = logging.getLogger(__name__)


@login_required
def tenant_select(request):
    tenants_users = TenantUser.objects.filter(
        user=request.user
    ).select_related('tenant').order_by('-is_primary', 'tenant__name')

    if request.method == 'POST':
        tenant_id = request.POST.get('tenant_id')
        try:
            tu = tenants_users.get(tenant_id=tenant_id)
            request.session['tenant_id'] = str(tu.tenant.id)
            logger.info('Tenant selecionado: user=%s tenant=%s', request.user.username, tu.tenant.name)
            return redirect('dashboard')
        except TenantUser.DoesNotExist:
            messages.error(request, 'Seleção inválida.')

    context = {
        'tenants_users': tenants_users,
    }
    return render(request, 'tenants/tenant_select.html', context)


class TenantListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Tenant
    template_name = 'tenants/tenant_list.html'
    context_object_name = 'tenants'
    permission_required = 'tenants.view_tenant'
    paginate_by = 10


class TenantCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = Tenant
    form_class = TenantCreateForm
    template_name = 'tenants/tenant_create.html'
    success_url = reverse_lazy('tenants:tenant_list')
    success_message = 'Empresa criada com sucesso!'
    permission_required = 'tenants.add_tenant'

    def form_valid(self, form):
        response = super().form_valid(form)
        tenant = self.object

        TenantSettings.objects.get_or_create(tenant=tenant)

        TenantUser.objects.create(
            user=self.request.user,
            tenant=tenant,
            role='admin',
            is_primary=True,
        )

        logger.info('Tenant criado: user=%s tenant=%s', self.request.user.username, tenant.name)
        return response


class TenantDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Tenant
    template_name = 'tenants/tenant_detail.html'
    context_object_name = 'tenant'
    permission_required = 'tenants.view_tenant'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tenant_users'] = TenantUser.objects.filter(
            tenant=self.object,
        ).select_related('user').order_by('-is_primary', 'user__username')
        return context


class TenantUserAddView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'tenants.add_tenantuser'

    def get(self, request, pk):
        tenant = get_object_or_404(Tenant, pk=pk)
        form = TenantUserAddForm(tenant=tenant)
        return render(request, 'tenants/tenant_user_add.html', {
            'tenant': tenant,
            'form': form,
        })

    def post(self, request, pk):
        tenant = get_object_or_404(Tenant, pk=pk)
        form = TenantUserAddForm(tenant=tenant, data=request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            role = form.cleaned_data['role']
            TenantUser.objects.create(
                user=user,
                tenant=tenant,
                role=role,
                is_primary=not TenantUser.objects.filter(tenant=tenant).exists(),
            )
            messages.success(
                request,
                f'Utilizador "{user.username}" adicionado como {dict(TenantUser.ROLE_CHOICES).get(role, role)}.',
            )
            logger.info('User added to tenant: user=%s tenant=%s role=%s', user.username, tenant.name, role)
            return redirect('tenants:tenant_detail', pk=tenant.pk)
        return render(request, 'tenants/tenant_user_add.html', {
            'tenant': tenant,
            'form': form,
        })


class TenantUserRemoveView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'tenants.delete_tenantuser'

    def post(self, request, pk, user_pk):
        tenant = get_object_or_404(Tenant, pk=pk)
        tu = get_object_or_404(TenantUser, tenant=tenant, user_id=user_pk)
        if tu.is_primary:
            messages.error(request, 'Não é possível remover o administrador principal.')
            return redirect('tenants:tenant_detail', pk=tenant.pk)
        username = tu.user.username
        tu.delete()
        messages.success(request, f'Utilizador "{username}" removido da empresa.')
        logger.info('User removed from tenant: user=%s tenant=%s', username, tenant.name)
        return redirect('tenants:tenant_detail', pk=tenant.pk)
