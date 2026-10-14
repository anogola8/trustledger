from django.urls import path

from . import views

app_name = 'dashboard'
urlpatterns = [
    path('', views.home, name='home'),
    path('users/', views.users, name='users'),
    path('users/<int:pk>/toggle/', views.toggle_user, name='toggle_user'),
    path('employers/', views.employers, name='employers'),
    path('employers/<int:pk>/<str:action>/', views.employer_action, name='employer_action'),
    path('verifications/', views.verifications, name='verifications'),
    path('flags/', views.flags, name='flags'),
    path('flags/<int:pk>/<str:action>/', views.flag_action, name='flag_action'),
]
