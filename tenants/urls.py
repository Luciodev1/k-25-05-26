from django.urls import path
from . import views

app_name = 'tenants'

urlpatterns = [
    path('selecionar/', views.tenant_select, name='tenant_select'),
    path('selecionar/<uuid:tenant_id>/confirmar/', views.tenant_confirm_switch, name='tenant_confirm_switch'),
    path('empresas/', views.TenantListView.as_view(), name='tenant_list'),
    path('empresas/nova/', views.TenantCreateView.as_view(), name='tenant_create'),
    path('empresas/<uuid:pk>/', views.TenantDetailView.as_view(), name='tenant_detail'),
    path('empresas/<uuid:pk>/adicionar-user/', views.TenantUserAddView.as_view(), name='tenant_user_add'),
    path('empresas/<uuid:pk>/remover-user/<int:user_pk>/', views.TenantUserRemoveView.as_view(), name='tenant_user_remove'),
]
