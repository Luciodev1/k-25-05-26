from django.shortcuts import redirect, render
from django.urls import reverse


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant_id = request.session.get('tenant_id')
        request.tenant = None
        request.tenant_user = None

        if request.user.is_authenticated:
            from .models import TenantUser

            allowed_prefixes = (
                '/selecionar/',
                '/accounts/',
                '/perfil/',
                reverse('logout'),
            )

            if tenant_id:
                try:
                    tu = TenantUser.objects.select_related('tenant').get(
                        user=request.user, tenant_id=tenant_id,
                    )
                    request.tenant = tu.tenant
                    request.tenant_user = tu
                except TenantUser.DoesNotExist:
                    self._clear_tenant_session(request)

            if request.tenant is None:
                tenant_users = list(
                    TenantUser.objects.filter(user=request.user).select_related('tenant')
                )
                total = len(tenant_users)
                if total == 0:
                    if not request.user.is_superuser:
                        if not any(request.path == p or request.path.startswith(p) for p in allowed_prefixes):
                            return render(request, 'tenants/no_access.html', status=403)
                elif total == 1:
                    request.tenant = tenant_users[0].tenant
                    request.tenant_user = tenant_users[0]
                    request.session['tenant_id'] = str(request.tenant.id)
                elif total > 1:
                    if not any(request.path == p or request.path.startswith(p) for p in allowed_prefixes):
                        return redirect('tenants:tenant_select')

        response = self.get_response(request)
        return response

    def _clear_tenant_session(self, request):
        request.session.pop('tenant_id', None)
        request.session.pop('tenant_name', None)
