from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LogoutView
from users.views import CustomLoginView
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render
from django.views.i18n import set_language

urlpatterns = [
    path('admin/', admin.site.urls),
    path('favicon.ico', views.favicon, name='favicon'),
    path('health/', views.health_check, name='health'),
    path('', views.dashboard, name='dashboard'),
    path('pending-deliveries-stat/', views.pending_deliveries_stat, name='pending_deliveries_stat'),

    # PWA
    path('manifest.json', views.pwa_manifest, name='pwa_manifest'),
    path('service-worker.js', views.service_worker, name='service_worker'),
    path('offline/', lambda request: render(request, 'offline.html'), name='offline'),

    # Portal do Cliente
    path('', include('portal.urls')),
    path('', include('portal.admin_urls')),

    path('', include('brands.urls')),
    path('', include('categories.urls')),
    path('', include('suppliers.urls')),
    path('', include('customers.urls')),
    path('', include('outflows.urls')),
    path('', include('products.urls')),
    path('', include('inflows.urls')),
    path('', include('accounts.urls')),
    path('', include('reports.urls')),
    path('', include('drivers.urls')),
    path('', include('payments.urls')),
    path('', include('users.urls')),
    path('', include('audit.urls')),
    path('', include('tenants.urls')),
    path('accounts/login/', CustomLoginView.as_view(), name='login'),
    path('accounts/logout/', LogoutView.as_view(), name='logout'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('i18n/', include('django.conf.urls.i18n')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'app.views.custom_404'
handler403 = 'app.views.custom_403'
handler500 = 'app.views.custom_500'
