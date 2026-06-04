from django.urls import path
from . import admin_views

app_name = 'portal_acessos'

urlpatterns = [
    path('portal-acessos/', admin_views.PortalAccessListView.as_view(), name='list'),
    path('portal-acessos/novo/', admin_views.PortalAccessCreateView.as_view(), name='create'),
    path('portal-acessos/<int:pk>/', admin_views.PortalAccessDetailView.as_view(), name='detail'),
    path('portal-acessos/<int:pk>/editar/', admin_views.PortalAccessUpdateView.as_view(), name='update'),
    path('portal-acessos/<int:pk>/remover/', admin_views.PortalAccessDeleteView.as_view(), name='delete'),
    path('portal-acessos/logs/', admin_views.PortalSessionLogAdminView.as_view(), name='session_logs'),
    path('portal-metricas/', admin_views.PortalAdminMetricsView.as_view(), name='metrics'),
]
