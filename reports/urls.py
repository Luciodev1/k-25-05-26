from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('reports/', views.report_index, name='report_index'),
    path('reports/outflows-by-customer/', views.outflows_by_customer_report, name='report_outflows_by_customer'),
    path('reports/deliveries/', views.deliveries_report, name='report_deliveries'),
    path('reports/customer-account/', views.customer_account_report, name='report_customer_account'),
    path('reports/supplier-account/', views.supplier_account_report, name='report_supplier_account'),
    path('reports/balances/', views.balances_report, name='report_balances'),
    path('reports/task-status/<str:task_id>/', views.task_status, name='report_task_status'),
    path('reports/download/<str:task_id>/', views.report_download, name='report_download'),
]
