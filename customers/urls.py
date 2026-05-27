from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    path('customers/list/', views.CustomerListView.as_view(), name='customer_list'),
    path('customers/create/', views.CustomerCreateView.as_view(), name='customer_create'),
    path('customers/<int:pk>/update/', views.CustomerUpdateView.as_view(), name='customer_update'),
    path('customers/<int:pk>/detail/', views.CustomerDetailView.as_view(), name='customer_detail'),
    path('customers/<int:pk>/delete/', views.CustomerDeleteView.as_view(), name='customer_delete'),
    path('customers/trash/', views.CustomerTrashListView.as_view(), name='customer_trash'),
    path('customers/<int:pk>/restore/', views.CustomerRestoreView.as_view(), name='customer_restore'),
    path('customers/<int:pk>/hard-delete/', views.CustomerHardDeleteView.as_view(), name='customer_hard_delete'),
]
