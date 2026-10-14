from django.conf import settings
from django.db import models


class TrustScore(models.Model):
    worker = models.ForeignKey('workers.WorkerProfile', on_delete=models.CASCADE, related_name='trust_scores')
    value = models.DecimalField(max_digits=5, decimal_places=2)
    components = models.JSONField(default=dict)
    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-computed_at', '-id']
        constraints = [models.CheckConstraint(condition=models.Q(value__gte=0, value__lte=100), name='score_0_100')]
        indexes = [models.Index(fields=['worker', 'computed_at'])]

    def __str__(self):
        return f'{self.worker}: {self.value}'


class WorkerBadge(models.Model):
    worker = models.ForeignKey('workers.WorkerProfile', on_delete=models.CASCADE, related_name='badges')
    code = models.CharField(max_length=30)
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['worker', 'code'], name='uniq_badge_per_worker')]
        ordering = ['awarded_at']

    @property
    def info(self):
        from .services import BADGES
        return BADGES.get(self.code, {'label': self.code, 'description': ''})

    def __str__(self):
        return f'{self.code} -> {self.worker}'


class FraudFlag(models.Model):
    class Severity(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'

    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        CLEARED = 'cleared', 'Cleared (false alarm)'
        CONFIRMED = 'confirmed', 'Confirmed'

    attestation = models.ForeignKey('attestations.Attestation', null=True, blank=True, on_delete=models.CASCADE, related_name='fraud_flags')
    employer = models.ForeignKey('employers.EmployerProfile', null=True, blank=True, on_delete=models.CASCADE, related_name='fraud_flags')
    rule_code = models.CharField(max_length=10)
    severity = models.CharField(max_length=6, choices=Severity.choices)
    reason = models.CharField(max_length=300)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status', 'severity']), models.Index(fields=['rule_code'])]

    def __str__(self):
        return f'{self.rule_code} ({self.severity})'
