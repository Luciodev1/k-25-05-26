import logging
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, FormView
from django.contrib.auth.views import LoginView
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)


class CustomLoginView(LoginView):
    template_name = 'registration/login.html'

    @method_decorator(ratelimit(key='ip', rate='5/15m', method='POST', block=False))
    def dispatch(self, request, *args, **kwargs):
        ip = request.META.get('REMOTE_ADDR', '')
        if self._is_blocked(ip):
            logger.warning('Login bloqueado (cool-down 30min): ip=%s', ip)
            from django.http import HttpResponse
            return HttpResponse(
                'Demasiadas tentativas de login. Aguarde 30 minutos antes de tentar novamente.',
                status=429,
                content_type='text/plain; charset=utf-8',
            )
        if getattr(request, 'limited', False):
            self._block_ip(ip)
            logger.warning('Rate limit excedido: ip=%s user=%s', ip, request.POST.get('username', ''))
            from django.http import HttpResponse
            return HttpResponse(
                'Demasiadas tentativas de login. Aguarde 30 minutos antes de tentar novamente.',
                status=429,
                content_type='text/plain; charset=utf-8',
            )
        return super().dispatch(request, *args, **kwargs)

    def _is_blocked(self, ip: str) -> bool:
        from django.core.cache import cache
        return cache.get(f'login_block_{ip}') is not None

    def _block_ip(self, ip: str) -> None:
        from django.core.cache import cache
        cache.set(f'login_block_{ip}', True, 1800)

    def _reset_rate_limit(self, ip: str) -> None:
        from django.core.cache import cache
        cache.delete(f'login_block_{ip}')

    def form_valid(self, form):
        user = form.get_user()
        logger.info('Login bem-sucedido: %s', user.username)
        ip = self.request.META.get('REMOTE_ADDR', '')
        self._reset_rate_limit(ip)
        from tenants.models import TenantUser
        tenant_users = list(TenantUser.objects.filter(user=user).select_related('tenant')[:2])
        if len(tenant_users) == 1:
            self.request.session['tenant_id'] = str(tenant_users[0].tenant.id)
        elif len(tenant_users) > 1:
            if 'tenant_id' not in self.request.session:
                pass
        return super().form_valid(form)

    def form_invalid(self, form):
        logger.warning(
            'Tentativa de login falhada: user=%s ip=%s',
            self.request.POST.get('username', ''),
            self.request.META.get('REMOTE_ADDR'),
        )
        return super().form_invalid(form)
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django import forms
from . import forms as user_forms


class UserListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = User
    template_name = 'user_list.html'
    context_object_name = 'users'
    permission_required = 'auth.view_user'
    paginate_by = 10

    def get_queryset(self):
        qs = User.objects.prefetch_related('groups').order_by('username')
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenantuser__tenant=tenant)
        return qs


@method_decorator(ratelimit(key='user_or_ip', rate='30/m', method='POST', block=True), name='dispatch')
class UserCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = User
    template_name = 'user_create.html'
    form_class = user_forms.UserCreateForm
    success_url = reverse_lazy('users:user_list')
    success_message = "Utilizador criado com sucesso!"
    permission_required = 'auth.add_user'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = getattr(self.request, 'tenant', None)
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['creating_tenant'] = getattr(self.request, 'tenant', None)
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            from tenants.models import TenantUser
            role = form.cleaned_data.get('tenant_role', 'operator')
            TenantUser.objects.get_or_create(
                user=self.object,
                tenant=tenant,
                defaults={'role': role},
            )
        return response


@method_decorator(ratelimit(key='user_or_ip', rate='30/m', method='POST', block=True), name='dispatch')
class UserUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    template_name = 'user_update.html'
    form_class = user_forms.UserUpdateForm
    success_url = reverse_lazy('users:user_list')
    success_message = "Utilizador atualizado com sucesso!"
    permission_required = 'auth.change_user'

    def get_queryset(self):
        qs = User.objects.prefetch_related('groups')
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenantuser__tenant=tenant)
        return qs


@method_decorator(ratelimit(key='user_or_ip', rate='20/m', method='POST', block=True), name='post')
class UserDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = User
    template_name = 'user_delete.html'
    success_url = reverse_lazy('users:user_list')
    permission_required = 'auth.delete_user'

    def get_queryset(self):
        qs = User.objects
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(tenantuser__tenant=tenant)
        return qs

    def post(self, request, *args, **kwargs):
        from django.db.models import ProtectedError
        try:
            messages.success(request, "Utilizador excluído com sucesso!")
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(request, "Não é possível eliminar este utilizador porque está associado a registos no sistema.")
            return redirect(self.success_url)


# --- Group Management ---

from collections import defaultdict

def get_grouped_permissions(group=None):
    permissions = Permission.objects.select_related('content_type').exclude(
        content_type__app_label__in=['admin', 'contenttypes', 'sessions']
    ).order_by('content_type__app_label', 'content_type__model', 'codename')
    
    grouped = defaultdict(list)
    group_perms_ids = set(group.permissions.values_list('id', flat=True)) if group else set()
    
    action_translations = {
        'add': 'Adicionar',
        'change': 'Editar',
        'delete': 'Eliminar',
        'view': 'Ver'
    }
    
    for perm in permissions:
        action = perm.codename.split('_')[0]
        model_name = perm.content_type.name.title()
        app_label = perm.content_type.app_label.title()
        
        action_name = action_translations.get(action, action.title())
        nice_name = f"{action_name} {model_name}"
        
        grouped[app_label].append({
            'id': perm.id,
            'name': nice_name,
            'selected': perm.id in group_perms_ids
        })
        
    return dict(grouped)


class GroupForm(forms.ModelForm):
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(),
        required=False
    )

    class Meta:
        model = Group
        fields = ['name', 'permissions']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {'name': 'Nome do Grupo'}


class GroupListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Group
    template_name = 'group_list.html'
    context_object_name = 'groups'
    permission_required = 'auth.view_group'

    def get_queryset(self):
        qs = Group.objects.prefetch_related('permissions')
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(user__tenantuser__tenant=tenant).distinct()
        return qs


@method_decorator(ratelimit(key='user_or_ip', rate='30/m', method='POST', block=True), name='dispatch')
class GroupCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = Group
    form_class = GroupForm
    template_name = 'group_create.html'
    success_url = reverse_lazy('users:group_list')
    success_message = "Grupo criado com sucesso!"
    permission_required = 'auth.add_group'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['grouped_permissions'] = get_grouped_permissions(None)
        return context


@method_decorator(ratelimit(key='user_or_ip', rate='30/m', method='POST', block=True), name='dispatch')
class GroupUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Group
    form_class = GroupForm
    template_name = 'group_update.html'
    success_url = reverse_lazy('users:group_list')
    success_message = "Grupo atualizado com sucesso!"
    permission_required = 'auth.change_group'

    def get_queryset(self):
        qs = Group.objects
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(user__tenantuser__tenant=tenant)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['grouped_permissions'] = get_grouped_permissions(self.object)
        return context


@method_decorator(ratelimit(key='user_or_ip', rate='20/m', method='POST', block=True), name='post')
class GroupDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Group
    template_name = 'group_delete.html'
    success_url = reverse_lazy('users:group_list')
    permission_required = 'auth.delete_group'

    def get_queryset(self):
        qs = Group.objects
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            qs = qs.filter(user__tenantuser__tenant=tenant)
        return qs

    def post(self, request, *args, **kwargs):
        from django.db.models import ProtectedError
        try:
            messages.success(request, "Grupo eliminado com sucesso!")
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(request, "Não é possível eliminar este grupo porque está atribuído a utilizadores.")
            return redirect(self.success_url)


from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Profile

@login_required
def user_profile(request):
    user = request.user

    profile, _ = Profile.objects.get_or_create(user=user)

    cargo = _get_user_cargo(user)

    grouped = _get_grouped_permissions_for_user(user)

    recent_activity = user.audit_logs.select_related('user')[:20] if hasattr(user, 'audit_logs') else []

    context = {
        'profile': profile,
        'user_cargo': cargo,
        'grouped_permissions': grouped,
        'recent_activity': recent_activity,
    }
    return render(request, 'user_profile.html', context)


@login_required
def profile_edit(request):
    user = request.user
    profile, _ = Profile.objects.get_or_create(user=user)

    if request.method == 'POST':
        user_form = user_forms.UserInfoForm(request.POST, instance=user)
        profile_form = user_forms.UserProfileForm(
            request.POST, request.FILES, instance=profile,
        )
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Perfil atualizado com sucesso!')
            logger.info('Perfil atualizado: user=%s', user.username)
            return redirect('users:user_profile')
        else:
            messages.error(request, 'Corrija os erros abaixo.')
    else:
        user_form = user_forms.UserInfoForm(instance=user)
        profile_form = user_forms.UserProfileForm(instance=profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'profile': profile,
        'user_cargo': _get_user_cargo(user),
    }
    return render(request, 'user_profile_edit.html', context)


def _get_user_cargo(user):
    if user.is_superuser:
        return "Administrador"
    elif user.groups.exists():
        return ", ".join(g.name for g in user.groups.all())
    return "Operador"


def _get_grouped_permissions_for_user(user):
    from django.contrib.auth.models import Permission

    if user.is_superuser:
        perms = Permission.objects.select_related('content_type').exclude(
            content_type__app_label__in=['admin', 'contenttypes', 'sessions']
        ).order_by('content_type__app_label', 'codename')
    else:
        perm_strs = user.get_all_permissions()
        q_filters = Q()
        for p_str in perm_strs:
            if '.' in p_str:
                app_label, codename = p_str.split('.')
                q_filters |= Q(content_type__app_label=app_label, codename=codename)
        if q_filters:
            perms = Permission.objects.filter(q_filters).select_related('content_type').order_by(
                'content_type__app_label', 'codename'
            )
        else:
            perms = []

    grouped = defaultdict(list)
    action_translations = {
        'add': 'Adicionar',
        'change': 'Editar',
        'delete': 'Eliminar',
        'view': 'Ver'
    }
    app_translations = {
        'Brands': 'Marcas', 'Categories': 'Categorias', 'Suppliers': 'Fornecedores',
        'Customers': 'Clientes', 'Products': 'Produtos', 'Inflows': 'Entradas',
        'Outflows': 'Saídas', 'Accounts': 'Contas e Extratos', 'Reports': 'Relatórios',
        'Drivers': 'Motoristas', 'Payments': 'Pagamentos', 'Users': 'Utilizadores',
        'Audit': 'Auditoria', 'Auth': 'Autenticação e Grupos',
    }

    for perm in perms:
        action = perm.codename.split('_')[0]
        model_name = perm.content_type.name.title()
        app_label = perm.content_type.app_label.title()
        nice_app = app_translations.get(app_label, app_label)
        action_name = action_translations.get(action, action.title())
        grouped[nice_app].append(f"{action_name} {model_name}")

    return dict(grouped)

