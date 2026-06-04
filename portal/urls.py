from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'portal'

urlpatterns = [
    path('portal/login/', views.CustomerLoginView.as_view(), name='login'),
    path('portal/logout/', LogoutView.as_view(next_page='portal:login'), name='logout'),
    path('portal/', views.PortalDashboardView.as_view(), name='dashboard'),
    path('portal/conta/', views.PortalAccountStatementView.as_view(), name='account_statement'),
    path('portal/conta/exportar/', views.PortalExportStatementView.as_view(), name='export_statement'),
    path('portal/entregas/', views.PortalDeliveriesView.as_view(), name='deliveries'),
    path('portal/pagamentos/', views.PortalPaymentsView.as_view(), name='payments'),
    path('portal/saidas/<int:pk>/', views.PortalOutflowDetailView.as_view(), name='outflow_detail'),
    path('portal/mudar-password/', views.PortalPasswordChangeView.as_view(), name='password_change'),
    path('portal/perfil/editar/', views.PortalProfileEditView.as_view(), name='profile_edit'),
    path('portal/sessoes/', views.PortalSessionLogView.as_view(), name='session_log'),

    # Password reset
    path('portal/recuperar-password/', views.PortalPasswordResetView.as_view(), name='password_reset'),
    path('portal/recuperar-password/enviado/', views.PortalPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('portal/recuperar-password/<uidb64>/<token>/', views.PortalPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('portal/recuperar-password/completo/', views.PortalPasswordResetCompleteView.as_view(), name='password_reset_complete'),


]
