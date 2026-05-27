from django.urls import path
from . import views

app_name = 'suppliers'

urlpatterns = [
    path('suppliers/list/', views.SupplierListView.as_view(), name='supplier_list'),
    path('suppliers/create/', views.SupplierCreateView.as_view(), name='supplier_create'),
    path('suppliers/<int:pk>/update/', views.SupplierUpdateView.as_view(), name='supplier_update'),
    path('suppliers/<int:pk>/detail/', views.SupplierDetailView.as_view(), name='supplier_detail'),
    path('suppliers/<int:pk>/delete/', views.SupplierDeleteView.as_view(), name='supplier_delete'),
    path('suppliers/trash/', views.SupplierTrashListView.as_view(), name='supplier_trash'),
    path('suppliers/<int:pk>/restore/', views.SupplierRestoreView.as_view(), name='supplier_restore'),
    path('suppliers/<int:pk>/hard-delete/', views.SupplierHardDeleteView.as_view(), name='supplier_hard_delete'),
]