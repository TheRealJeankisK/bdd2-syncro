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
    path('artistas/', views.artistas_list, name='artistas_list'),
    path('artistas/crear/', views.artista_crear, name='artista_crear'),
    path('artistas/editar/<int:artista_id>/', views.artista_editar, name='artista_editar'),
    path('albumes/', views.albumes_list, name='albumes_list'),
    path('albumes/crear/', views.album_crear, name='album_crear'),
    path('albumes/editar/<int:album_id>/', views.album_editar, name='album_editar'),
    path('playlists/', views.playlists_list, name='playlists_list'),
    path('playlists/crear/', views.playlist_crear, name='playlist_crear'),
    path('playlists/editar/<int:playlist_id>/', views.playlist_editar, name='playlist_editar'),
    path('reportes/', views.reportes_view, name='reportes_view'),
    path('canciones/play/<int:cancion_id>/', views.simular_play, name='simular_play'),
    path('reportes/liquidar/', views.ejecutar_liquidacion, name='ejecutar_liquidacion'),
]
