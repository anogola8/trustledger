from django.urls import path

from . import views

app_name = 'workers'
urlpatterns = [
    path('workers/profile/', views.manage, name='manage'),
    path('workers/profile/edit/', views.edit_profile, name='edit'),
    path('workers/skills/add/', views.add_skill, name='add_skill'),
    path('workers/skills/<int:pk>/delete/', views.delete_skill, name='delete_skill'),
    path('workers/certificates/add/', views.add_certificate, name='add_certificate'),
    path('workers/certificates/<int:pk>/file/', views.certificate_file, name='certificate_file'),
    path('workers/certificates/<int:pk>/delete/', views.delete_certificate, name='delete_certificate'),
    path('workers/experience/add/', views.add_experience, name='add_experience'),
    path('workers/experience/<int:pk>/delete/', views.delete_experience, name='delete_experience'),
    path('workers/timeline/', views.timeline, name='timeline'),
    path('workers/cv.pdf', views.cv_pdf, name='cv'),
    path('w/<slug:slug>/', views.public_profile, name='public'),
    path('w/<slug:slug>/qr.png', views.profile_qr, name='qr'),
        path('workers/portfolio/', views.portfolio, name='portfolio'),
    path('w/<slug:slug>/portfolio/', views.portfolio_public, name='portfolio_public'),
    path('workers/explore/', views.explore, name='explore'),
]