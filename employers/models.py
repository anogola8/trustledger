from django.conf import settings
from django.db import models
from django.utils import timezone


class EmployerProfile(models.Model):
    class OrgType(models.TextChoices):
        HOUSEHOLD = 'household', 'Household / individual'
        BUSINESS = 'business', 'Small business'
        NGO = 'ngo', 'NGO / CBO'
        AGENCY = 'agency', 'Recruitment agency'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending approval'
        APPROVED = 'approved', 'Approved'
        SUSPENDED = 'suspended', 'Suspended'

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='employer_profile')
    organisation_name = models.CharField(max_length=150)
    org_type = models.CharField(max_length=12, choices=OrgType.choices, default=OrgType.BUSINESS)
    registration_number = models.CharField(max_length=60, blank=True)
    description = models.TextField(blank=True, max_length=1000)
    location = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    approved_at = models.DateTimeField(null=True, blank=True)
    # Ed25519 signing key pair: public key is published; private key is encrypted at rest.
    key_id = models.CharField(max_length=40, blank=True)
    public_key = models.CharField(max_length=64, blank=True)
    encrypted_private_key = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['organisation_name']
        indexes = [models.Index(fields=['status'])]

    def __str__(self):
        return self.organisation_name

    @property
    def can_issue(self):
        return self.status == self.Status.APPROVED and bool(self.public_key) and self.user.is_active

    def approve(self):
        from attestations.crypto import generate_keypair
        if not self.public_key:
            self.key_id, self.public_key, self.encrypted_private_key = generate_keypair()
        self.status = self.Status.APPROVED
        self.approved_at = timezone.now()
        self.save()

    def suspend(self):
        self.status = self.Status.SUSPENDED
        self.save(update_fields=['status'])


class EmployerRating(models.Model):
    """A structured rating of a worker's engagement, given by the employer on an active attestation."""
    attestation = models.OneToOneField('attestations.Attestation', on_delete=models.CASCADE, related_name='rating')
    employer = models.ForeignKey(EmployerProfile, on_delete=models.CASCADE, related_name='ratings_given')
    worker = models.ForeignKey('workers.WorkerProfile', on_delete=models.CASCADE, related_name='ratings_received')
    score = models.PositiveSmallIntegerField()
    punctuality = models.PositiveSmallIntegerField(default=3)
    quality = models.PositiveSmallIntegerField(default=3)
    honesty = models.PositiveSmallIntegerField(default=3)
    comment = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(score__gte=1, score__lte=5), name='rating_score_1_5'),
        ]
        indexes = [models.Index(fields=['worker'])]

    def __str__(self):
        return f'{self.score}/5 for {self.worker}'
