from django.urls import path

from . import views

app_name = 'disputes'
urlpatterns = [
    path('', views.dispute_list, name='list'),
    path('new/<uuid:att_id>/', views.new_dispute, name='new'),
    path('<int:pk>/', views.detail, name='detail'),
    path('<int:pk>/evidence/', views.evidence, name='evidence'),
    path('<int:pk>/resolve/', views.resolve, name='resolve'),
]
