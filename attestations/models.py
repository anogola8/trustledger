import uuid

from django.db import models
from django.db.models import F, Q


class Attestation(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Awaiting worker confirmation'
        ACTIVE = 'active', 'Active'
        DISPUTED = 'disputed', 'Disputed'
        REVOKED = 'revoked', 'Revoked'
        REJECTED = 'rejected', 'Rejected by worker'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    worker = models.ForeignKey('workers.WorkerProfile', on_delete=models.CASCADE, related_name='attestations')
    employer = models.ForeignKey('employers.EmployerProfile', on_delete=models.PROTECT, related_name='attestations')
    role_title = models.CharField(max_length=120)
    description = models.TextField(blank=True, max_length=1000)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text='Leave empty if the engagement is ongoing')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    verification_code = models.CharField(max_length=20, unique=True, null=True, blank=True)
    payload_hash = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_reason = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [models.CheckConstraint(condition=Q(end_date__isnull=True) | Q(end_date__gte=F('start_date')), name='att_dates_valid')]
        indexes = [models.Index(fields=['worker', 'status']), models.Index(fields=['employer', 'status']),
                   models.Index(fields=['created_at'])]

    def __str__(self):
        return f'{self.role_title} - {self.worker} ({self.status})'

    @property
    def is_verifiable(self):
        return bool(self.verification_code) and self.status in (self.Status.ACTIVE, self.Status.DISPUTED, self.Status.REVOKED)


class AttestationSignature(models.Model):
    attestation = models.OneToOneField(Attestation, on_delete=models.CASCADE, related_name='signature')
    signature = models.TextField()
    key_id = models.CharField(max_length=40)
    algorithm = models.CharField(max_length=20, default='Ed25519')
    signed_at = models.DateTimeField()

    def __str__(self):
        return f'sig:{self.key_id}'
