from django.urls import path
from . import views

app_name = 'outflows'

urlpatterns = [
    path('outflows/list/', views.OutflowListView.as_view(), name='outflow_list'),
    path('outflows/create/', views.OutflowCreateView.as_view(), name='outflow_create'),
    path('outflows/<int:pk>/detail/', views.OutflowDetailView.as_view(), name='outflow_detail'),
    path('outflows/<int:pk>/edit/', views.OutflowUpdateView.as_view(), name='outflow_update'),
    path('outflows/<int:pk>/delete/', views.OutflowDeleteView.as_view(), name='outflow_delete'),
    path('outflows/<int:pk>/delivery/', views.DeliveryCreateView.as_view(), name='delivery_create'),
    path('deliveries/<int:pk>/shipping-guide/', views.DeliveryShippingGuideView.as_view(), name='delivery_shipping_guide'),
    path('deliveries/<int:pk>/confirm-weight/', views.DeliveryConfirmWeightView.as_view(), name='delivery_confirm_weight'),
    path('outflows/trash/', views.OutflowTrashListView.as_view(), name='outflow_trash'),
    path('outflows/<int:pk>/restore/', views.OutflowRestoreView.as_view(), name='outflow_restore'),
    path('outflows/<int:pk>/hard-delete/', views.OutflowHardDeleteView.as_view(), name='outflow_hard_delete'),
    path('deliveries/<int:pk>/delete/', views.DeliveryDeleteView.as_view(), name='delivery_delete'),
    path('deliveries/trash/', views.DeliveryTrashListView.as_view(), name='delivery_trash'),
    path('deliveries/<int:pk>/restore/', views.DeliveryRestoreView.as_view(), name='delivery_restore'),
    path('deliveries/<int:pk>/hard-delete/', views.DeliveryHardDeleteView.as_view(), name='delivery_hard_delete'),
]
