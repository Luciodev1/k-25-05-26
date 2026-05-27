from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('accounts/customer/<int:pk>/', views.CustomerAccountListView.as_view(), name='customer_account'),
    path('accounts/customer/<int:pk>/payment/', views.CustomerPaymentCreateView.as_view(), name='customer_payment'),
    path('accounts/supplier/<int:pk>/', views.SupplierAccountListView.as_view(), name='supplier_account'),
    path('accounts/supplier/<int:pk>/payment/', views.SupplierPaymentCreateView.as_view(), name='supplier_payment'),
    path('accounts/customer-balances/', views.CustomerBalanceListView.as_view(), name='customer_balances'),
    path('accounts/supplier-balances/', views.SupplierBalanceListView.as_view(), name='supplier_balances'),
]
