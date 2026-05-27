from django.urls import path
from . import views

app_name = 'inflows'

urlpatterns = [
    path('inflows/list/', views.InflowListView.as_view(), name='inflow_list'),
    path('inflows/create/', views.InflowCreateView.as_view(), name='inflow_create'),
    path('inflows/<int:pk>/detail/', views.InflowDetailView.as_view(), name='inflow_detail'),
    path('inflows/<int:pk>/edit/', views.InflowUpdateView.as_view(), name='inflow_update'),
    path('inflows/<int:pk>/delete/', views.InflowDeleteView.as_view(), name='inflow_delete'),
    path('inflows/trash/', views.InflowTrashListView.as_view(), name='inflow_trash'),
    path('inflows/<int:pk>/restore/', views.InflowRestoreView.as_view(), name='inflow_restore'),
    path('inflows/<int:pk>/hard-delete/', views.InflowHardDeleteView.as_view(), name='inflow_hard_delete'),
]
