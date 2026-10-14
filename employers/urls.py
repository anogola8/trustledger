from django.urls import path

from . import views

app_name = 'employers'
urlpatterns = [
    path('profile/', views.edit_profile, name='edit'),
    path('verify-worker/', views.verify_worker, name='verify_worker'),
]
