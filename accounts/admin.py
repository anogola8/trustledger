from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class TrustUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active')
    fieldsets = UserAdmin.fieldsets + (('TrustLedger', {'fields': ('role', 'phone')}),)
