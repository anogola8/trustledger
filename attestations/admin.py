from django.contrib import admin

from .models import Attestation, AttestationSignature


@admin.register(Attestation)
class AttestationAdmin(admin.ModelAdmin):
    list_display = ('role_title', 'worker', 'employer', 'status', 'verification_code', 'created_at')
    list_filter = ('status',)
    readonly_fields = ('payload_hash', 'verification_code', 'confirmed_at')


admin.site.register(AttestationSignature)
