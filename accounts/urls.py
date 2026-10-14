from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = 'accounts'
urlpatterns = [
    path('login/', views.TrustLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('register/worker/', views.register_worker, name='register_worker'),
    path('register/employer/', views.register_employer, name='register_employer'),
    path('verify-email/<uuid:token>/', views.verify_email, name='verify_email'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html',
        email_template_name='accounts/emails/password_reset_email.html',
        subject_template_name='accounts/emails/password_reset_subject.txt',
        success_url='/accounts/password-reset/done/',
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html',
    ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url='/accounts/password-reset-complete/',
    ), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html',
    ), name='password_reset_complete'),    path('google-login/', lambda r: __import__('django.shortcuts', fromlist=['render']).render(r, 'accounts/google_coming_soon.html'), name='google_coming_soon'),
]