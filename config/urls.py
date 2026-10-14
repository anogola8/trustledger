from django.conf import settings
from django.contrib import admin
from core.setup_admin import create_admin
from django.urls import include, path
from django.views.static import serve
from django.urls import re_path

urlpatterns = [
    path('setup-admin/', create_admin, name='setup_admin'),
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('', include('workers.urls')),
    path('employers/', include('employers.urls')),
    path('attestations/', include('attestations.urls')),
    path('verify/', include('verification.urls')),
    path('disputes/', include('disputes.urls')),
    path('notifications/', include('notifications.urls')),
    path('audit/', include('audit.urls')),
    path('api/', include('core.api_urls')),
]
if settings.SERVE_MEDIA:
    urlpatterns += [re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT})]
