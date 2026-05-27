from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('pagamentos/', views.PaymentListView.as_view(), name='payment_list'),
    path('pagamentos/novo/', views.PaymentCreateView.as_view(), name='payment_create'),
    path('pagamentos/<int:pk>/detalhe/', views.PaymentDetailView.as_view(), name='payment_detail'),
    path('pagamentos/<int:pk>/editar/', views.PaymentUpdateView.as_view(), name='payment_update'),
    path('pagamentos/<int:pk>/eliminar/', views.PaymentDeleteView.as_view(), name='payment_delete'),
    path('pagamentos/lixeira/', views.PaymentTrashListView.as_view(), name='payment_trash'),
    path('pagamentos/<int:pk>/restaurar/', views.PaymentRestoreView.as_view(), name='payment_restore'),
    path('pagamentos/<int:pk>/eliminar-permanente/', views.PaymentHardDeleteView.as_view(), name='payment_hard_delete'),
]
