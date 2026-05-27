from django.urls import path
from . import views

app_name = 'categories'

urlpatterns = [
    path('categories/list/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/create/', views.CategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/update/', views.CategoryUpdateView.as_view(), name='category_update'),
    path('categories/<int:pk>/detail/', views.CategoryDetailView.as_view(), name='category_detail'),
    path('categories/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),
    path('categories/trash/', views.CategoryTrashListView.as_view(), name='category_trash'),
    path('categories/<int:pk>/restore/', views.CategoryRestoreView.as_view(), name='category_restore'),
    path('categories/<int:pk>/hard-delete/', views.CategoryHardDeleteView.as_view(), name='category_hard_delete'),
]