from django.contrib import admin

from .models import EmployerProfile, EmployerRating


@admin.register(EmployerProfile)
class EmployerAdmin(admin.ModelAdmin):
    list_display = ('organisation_name', 'org_type', 'status', 'approved_at')
    list_filter = ('status', 'org_type')
    exclude = ('encrypted_private_key',)
    actions = ['approve_selected']

    @admin.action(description='Approve selected employers (generate signing keys)')
    def approve_selected(self, request, queryset):
        for e in queryset:
            e.approve()


admin.site.register(EmployerRating)
