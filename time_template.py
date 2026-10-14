"""Isolate the landing template rendering time."""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import time
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.db import connection, reset_queries
from django.conf import settings
settings.DEBUG = True

from workers.models import WorkerProfile, Skill
from attestations.models import Attestation
from django.db.models import Count, Q, Max

# Build the same context the landing view builds
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

ctx = {
    'featured_workers': featured_workers,
    'top_skills': top_skills,
    'stats': stats,
}

# Render the whole template
rf = RequestFactory()
request = rf.get('/')

from django.contrib.auth.models import AnonymousUser
request.user = AnonymousUser()

print("=" * 60)
print("TEMPLATE RENDER TIMING")
print("=" * 60)

reset_queries()
t0 = time.time()
html = render_to_string('core/landing.html', ctx, request=request)
elapsed = (time.time() - t0) * 1000
print(f"Full template:          {elapsed:8.1f} ms  ({len(html)} bytes)")

# Render just the featured section (avatar tags)
from django.template import Template, Context
mini = '''
{% load avatar_tags %}
{% for w in featured_workers %}{% avatar w 72 %}{% endfor %}
'''
t = Template(mini)
reset_queries()
t0 = time.time()
out = t.render(Context(ctx))
elapsed = (time.time() - t0) * 1000
print(f"8 avatar tags only:     {elapsed:8.1f} ms  ({len(out)} bytes)")

# Render without avatars
mini2 = '''
{% for w in featured_workers %}{{ w.full_name }}{% endfor %}
'''
t2 = Template(mini2)
reset_queries()
t0 = time.time()
out2 = t2.render(Context(ctx))
elapsed = (time.time() - t0) * 1000
print(f"8 names only (no avatar){elapsed:8.1f} ms")

print("=" * 60)