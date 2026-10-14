from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditLog(models.Model):
    """Append-only log. Each entry stores the hash of the previous entry (hash chain)."""
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='audit_entries')
    action = models.CharField(max_length=60)
    entity_type = models.CharField(max_length=40, blank=True)
    entity_id = models.CharField(max_length=64, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    prev_hash = models.CharField(max_length=64)
    entry_hash = models.CharField(max_length=64, unique=True)

    class Meta:
        ordering = ['id']
        indexes = [models.Index(fields=['action']), models.Index(fields=['entity_type', 'entity_id']), models.Index(fields=['created_at'])]

    def __str__(self):
        return f'{self.created_at:%Y-%m-%d %H:%M} {self.action}'
