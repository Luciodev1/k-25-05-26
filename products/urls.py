from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('products/list/', views.ProductListView.as_view(), name='product_list'),
    path('products/create/', views.ProductCreateView.as_view(), name='product_create'),
    path('products/<int:pk>/update/', views.ProductUpdateView.as_view(), name='product_update'),
    path('products/<int:pk>/detail/', views.ProductDetailView.as_view(), name='product_detail'),
    path('products/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product_delete'),
    path('products/bulk-delete/', views.ProductBulkDeleteView.as_view(), name='product_bulk_delete'),
    path('products/trash/', views.ProductTrashListView.as_view(), name='product_trash'),
    path('products/<int:pk>/restore/', views.ProductRestoreView.as_view(), name='product_restore'),
    path('products/<int:pk>/hard-delete/', views.ProductHardDeleteView.as_view(), name='product_hard_delete'),
]
