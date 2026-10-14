import secrets

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.db.models import F, Q
from django.utils.text import slugify

from core.validators import validate_document, validate_image

def private_storage():
    """Callable storage so the absolute path is never frozen into migrations."""
    return FileSystemStorage(location=str(settings.PRIVATE_ROOT))


def _new_slug(name):
    base = slugify(name)[:30] or 'worker'
    return f'{base}-{secrets.token_hex(3)}'


class WorkerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='worker_profile')
    full_name = models.CharField(max_length=120)
    headline = models.CharField(max_length=140, blank=True, help_text='e.g. Experienced boda boda rider')
    bio = models.TextField(blank=True, max_length=1200)
    location = models.CharField(max_length=100, blank=True)
    photo = models.ImageField(upload_to='photos/', blank=True, validators=[validate_image])
    slug = models.SlugField(max_length=50, unique=True, editable=False)
    show_skills = models.BooleanField(default=True)
    show_certificates = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['full_name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _new_slug(self.full_name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('workers:public', args=[self.slug])


class Skill(models.Model):
    class Level(models.IntegerChoices):
        BEGINNER = 1, 'Beginner'
        INTERMEDIATE = 2, 'Intermediate'
        ADVANCED = 3, 'Advanced'

    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='skills')
    name = models.CharField(max_length=60)
    level = models.IntegerField(choices=Level.choices, default=Level.INTERMEDIATE)
    years = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['-level', 'name']
        constraints = [models.UniqueConstraint(fields=['worker', 'name'], name='uniq_skill_per_worker')]

    def __str__(self):
        return self.name


class Certificate(models.Model):
    """Self-declared (Tier 0) unless an institution later signs it. Stored privately."""
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='certificates')
    title = models.CharField(max_length=120)
    issuing_body = models.CharField(max_length=120, blank=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    file = models.FileField(upload_to='certificates/', storage=private_storage, validators=[validate_document])
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title


class WorkExperience(models.Model):
    """Self-declared timeline entry. Always labelled 'self-declared' to separate claims from proof."""
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='experiences')
    employer_name = models.CharField(max_length=150)
    role_title = models.CharField(max_length=120)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True, max_length=800)

    class Meta:
        ordering = ['-start_date']
        constraints = [models.CheckConstraint(condition=Q(end_date__isnull=True) | Q(end_date__gte=F('start_date')), name='exp_dates_valid')]

    def __str__(self):
        return f'{self.role_title} at {self.employer_name}'
