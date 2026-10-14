from django.urls import path

from . import views

app_name = 'attestations'
urlpatterns = [
    path('', views.attestation_list, name='list'),
    path('issue/', views.issue, name='issue'),
    path('<uuid:pk>/', views.detail, name='detail'),
    path('<uuid:pk>/confirm/', views.confirm, name='confirm'),
    path('<uuid:pk>/reject/', views.reject, name='reject'),
    path('<uuid:pk>/revoke/', views.revoke, name='revoke'),
    path('<uuid:pk>/rate/', views.rate, name='rate'),
]
