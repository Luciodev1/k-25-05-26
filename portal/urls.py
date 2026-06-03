from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'portal'

urlpatterns = [
    path('portal/login/', views.CustomerLoginView.as_view(), name='login'),
    path('portal/logout/', LogoutView.as_view(next_page='portal:login'), name='logout'),
    path('portal/', views.PortalDashboardView.as_view(), name='dashboard'),
    path('portal/conta/', views.PortalAccountStatementView.as_view(), name='account_statement'),
    path('portal/entregas/', views.PortalDeliveriesView.as_view(), name='deliveries'),
    path('portal/pagamentos/', views.PortalPaymentsView.as_view(), name='payments'),
    path('portal/mudar-password/', views.PortalPasswordChangeView.as_view(), name='password_change'),
]
