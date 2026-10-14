from django.contrib import admin

from .models import FraudFlag, TrustScore, WorkerBadge

admin.site.register([TrustScore, WorkerBadge, FraudFlag])
