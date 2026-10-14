from django.urls import path

from . import views

app_name = 'core'
urlpatterns = [
    path('', views.landing, name='landing'),
    path('healthz', views.healthz, name='healthz'),
]
