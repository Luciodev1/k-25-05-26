from django.urls import path
from . import views

app_name = 'brands'

urlpatterns = [
    path('brands/list/', views.BrandListView.as_view(), name='brand_list'),
    path('brands/create/', views.BrandCreateView.as_view(), name='brand_create'),
    path('brands/<int:pk>/update/', views.BrandUpdateView.as_view(), name='brand_update'),
    path('brands/<int:pk>/detail/', views.BrandDetailView.as_view(), name='brand_detail'),
    path('brands/<int:pk>/delete/', views.BrandDeleteView.as_view(), name='brand_delete'),
    path('brands/trash/', views.BrandTrashListView.as_view(), name='brand_trash'),
    path('brands/<int:pk>/restore/', views.BrandRestoreView.as_view(), name='brand_restore'),
    path('brands/<int:pk>/hard-delete/', views.BrandHardDeleteView.as_view(), name='brand_hard_delete'),
]