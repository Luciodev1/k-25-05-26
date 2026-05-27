from django.urls import path
from . import views

app_name = 'drivers'

urlpatterns = [
    path('drivers/list/', views.DriverListView.as_view(), name='driver_list'),
    path('drivers/create/', views.DriverCreateView.as_view(), name='driver_create'),
    path('drivers/<int:pk>/detail/', views.DriverDetailView.as_view(), name='driver_detail'),
    path('drivers/<int:pk>/update/', views.DriverUpdateView.as_view(), name='driver_update'),
    path('drivers/<int:pk>/delete/', views.DriverDeleteView.as_view(), name='driver_delete'),
    path('drivers/trash/', views.DriverTrashListView.as_view(), name='driver_trash'),
    path('drivers/<int:pk>/restore/', views.DriverRestoreView.as_view(), name='driver_restore'),
    path('drivers/<int:pk>/hard-delete/', views.DriverHardDeleteView.as_view(), name='driver_hard_delete'),
]
