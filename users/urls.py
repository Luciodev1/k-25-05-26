from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/create/', views.UserCreateView.as_view(), name='user_create'),
    path('users/<int:pk>/update/', views.UserUpdateView.as_view(), name='user_update'),
    path('users/<int:pk>/delete/', views.UserDeleteView.as_view(), name='user_delete'),
    path('grupos/', views.GroupListView.as_view(), name='group_list'),
    path('grupos/novo/', views.GroupCreateView.as_view(), name='group_create'),
    path('grupos/<int:pk>/editar/', views.GroupUpdateView.as_view(), name='group_update'),
    path('grupos/<int:pk>/eliminar/', views.GroupDeleteView.as_view(), name='group_delete'),
    path('perfil/', views.user_profile, name='user_profile'),
    path('perfil/editar/', views.profile_edit, name='profile_edit'),
]
