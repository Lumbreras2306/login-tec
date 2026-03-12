from django.urls import path

from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('battle/', views.battle_view, name='battle'),
    path('pokemon/<str:name>/', views.pokemon_detail_view, name='pokemon-detail'),
    path('api/pokemon/', views.pokemon_list_api, name='pokemon-list-api'),
    path('api/pokemon/<str:name>/', views.pokemon_detail_api, name='pokemon-detail-api'),
]
