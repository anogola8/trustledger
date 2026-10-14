from django.urls import path

from . import views

app_name = 'verification'
urlpatterns = [
    path('', views.home, name='home'),
    path('<str:code>/', views.result, name='result'),
    path('<str:code>/qr.png', views.qr, name='qr'),
    path('<str:code>/report.pdf', views.report_pdf, name='report'),
]
