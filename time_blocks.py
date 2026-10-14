"""Time each section of the landing template."""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import time
from django.template import Template, Context
from django.test import RequestFactory
from django.db import connection, reset_queries
from django.conf import settings
settings.DEBUG = True

from workers.models import WorkerProfile, Skill
from attestations.models import Attestation
from django.db.models import Count, Q, Max

featured_workers = list(
    WorkerProfile.objects
    .annotate(
        active_count=Count('attestations', filter=Q(attestations__status='active')),
        latest_score=Max('trust_scores__value'),
    )
    .filter(active_count__gte=1, latest_score__isnull=False)
    .order_by('-latest_score', '-active_count')[:8]
)

top_skills = list(
    Skill.objects.values('name').annotate(n=Count('id')).order_by('-n')[:12]
)

stats = {
    'workers': WorkerProfile.objects.count(),
    'attestations': Attestation.objects.count(),
    'active': Attestation.objects.filter(status='active').count(),
}

# Build a lightweight context — just what templates need
ctx = Context({
    'featured_workers': featured_workers,
    'top_skills': top_skills,
    'stats': stats,
})

# Test tiny pieces
tests = [
    ("Plain static", "Hello world"),
    ("Extends base only", "{% extends 'base.html' %}{% block content %}test{% endblock %}"),
    ("Full template", open('templates/core/landing.html').read()),
]

print("=" * 60)
print("PIECE-BY-PIECE TIMING")
print("=" * 60)

for name, source in tests:
    t = Template(source)
    # Warm up
    try:
        t.render(ctx)
    except Exception as e:
        print(f"{name:30}  ERROR: {e}")
        continue
    # Timed
    t0 = time.time()
    for _ in range(5):
        try:
            t.render(ctx)
        except Exception:
            pass
    elapsed = (time.time() - t0) * 1000 / 5
    print(f"{name:30}  {elapsed:8.1f} ms (avg over 5)")

print("=" * 60)