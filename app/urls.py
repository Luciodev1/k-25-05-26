from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LogoutView
from users.views import CustomLoginView
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', views.health_check, name='health'),
    path('', views.dashboard, name='dashboard'),
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
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'app.views.custom_404'
handler403 = 'app.views.custom_403'
handler500 = 'app.views.custom_500'
