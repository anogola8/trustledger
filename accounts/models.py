import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        WORKER = 'worker', 'Worker'
        EMPLOYER = 'employer', 'Employer'
        ADMIN = 'admin', 'Administrator'

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.WORKER)
    phone = models.CharField(max_length=20, blank=True)

    class Meta:
        indexes = [models.Index(fields=['role', 'is_active'])]

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)

    @property
    def is_worker(self):
        return self.role == self.Role.WORKER

    @property
    def is_employer(self):
        return self.role == self.Role.EMPLOYER

    @property
    def is_email_verified(self):
        ev = getattr(self, 'email_verification', None)
        return bool(ev and ev.verified_at)
    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN or self.is_superuser


class EmailVerification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='email_verification')
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    def is_valid(self):
        from django.utils import timezone
        return self.verified_at is None and (timezone.now() - self.created_at).days < 3

    def mark_verified(self):
        from django.utils import timezone
        self.verified_at = timezone.now()
        self.save(update_fields=['verified_at'])

    def __str__(self):
        return f'EmailVerification for {self.user.email}'