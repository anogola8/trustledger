from django.contrib import admin

from .models import Certificate, Skill, WorkerProfile, WorkExperience

admin.site.register([WorkerProfile, Skill, Certificate, WorkExperience])
