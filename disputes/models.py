from django.conf import settings
from django.db import models

from workers.models import private_storage
from core.validators import validate_document


class Dispute(models.Model):
    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        UPHELD = 'upheld', 'Resolved: attestation upheld'
        REVOKED = 'revoked', 'Resolved: attestation revoked'

    attestation = models.ForeignKey('attestations.Attestation', on_delete=models.CASCADE, related_name='disputes')
    raised_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='disputes_raised')
    reason = models.TextField(max_length=1000)
    evidence = models.FileField(upload_to='evidence/', storage=private_storage, blank=True, validators=[validate_document])
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.OPEN)
    decision_note = models.TextField(blank=True, max_length=1000)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='disputes_resolved')
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status', 'created_at'])]

    def __str__(self):
        return f'Dispute #{self.pk} ({self.status})'
