from django.urls import path
from . import views

app_name = 'audit'

urlpatterns = [
    path('auditoria/', views.AuditLogListView.as_view(), name='audit_list'),
    path('atividade/', views.ActivityFeedView.as_view(), name='activity_feed'),
]
