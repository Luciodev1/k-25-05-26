def current_tenant(request):
    ctx = {
        'current_tenant': getattr(request, 'tenant', None),
        'tenant_user': getattr(request, 'tenant_user', None),
        'available_tenants': [],
    }
    if request.user.is_authenticated:
        from .models import TenantUser
        ctx['available_tenants'] = list(
            TenantUser.objects.filter(
                user=request.user,
            ).select_related('tenant').order_by('-is_primary', 'tenant__name')
        )
    return ctx
