from django.db import models


class VerificationRequest(models.Model):
    class Method(models.TextChoices):
        CODE = 'code', 'Code entry'
        LINK = 'link', 'Link / QR scan'
        API = 'api', 'API'

    attestation = models.ForeignKey('attestations.Attestation', null=True, blank=True, on_delete=models.SET_NULL, related_name='verifications')
    code_queried = models.CharField(max_length=30, blank=True)
    method = models.CharField(max_length=6, choices=Method.choices, default=Method.LINK)
    result = models.CharField(max_length=12)
    ip_hash = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['created_at']), models.Index(fields=['result']), models.Index(fields=['attestation', 'created_at'])]

    def __str__(self):
        return f'{self.code_queried} -> {self.result}'
