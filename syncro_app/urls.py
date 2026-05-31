from django.urls import path
from . import views

urlpatterns = [
    path('', views.usuarios_list, name='usuarios_list'),
    path('usuarios/', views.usuarios_list, name='usuarios_list'),
    path('usuarios/crear/', views.usuario_crear, name='usuario_crear'),
    path('usuarios/editar/<int:user_id>/', views.usuario_editar, name='usuario_editar'),
    path('usuarios/eliminar/<int:user_id>/', views.usuario_eliminar, name='usuario_eliminar'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('usuarios/exportar/json/', views.usuario_exportar_json, name='usuario_exportar_json'),
]
