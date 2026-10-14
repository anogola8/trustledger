"""Time each part of the landing view."""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import time
from django.db import connection, reset_queries
from django.conf import settings
settings.DEBUG = True

from workers.models import WorkerProfile, Skill
from attestations.models import Attestation
from django.db.models import Count, Q, Max

def timeit(label, fn):
    reset_queries()
    t0 = time.time()
    result = fn()
    elapsed = (time.time() - t0) * 1000
    n = len(connection.queries)
    db_time = sum(float(q['time']) for q in connection.queries) * 1000
    print(f"{label:40} {elapsed:8.1f} ms  ({n} queries, {db_time:.1f} ms DB)")
    return result

print("=" * 75)
print("LANDING PAGE — PART-BY-PART TIMING")
print("=" * 75)

featured_workers = timeit('featured_workers query', lambda:
    list(WorkerProfile.objects
        .annotate(
            active_count=Count('attestations', filter=Q(attestations__status='active')),
            latest_score=Max('trust_scores__value'),
        )
        .filter(active_count__gte=1, latest_score__isnull=False)
        .order_by('-latest_score', '-active_count')[:8])
)

top_skills = timeit('top_skills query', lambda:
    list(Skill.objects.values('name').annotate(n=Count('id')).order_by('-n')[:12])
)

workers_count = timeit('workers count', lambda: WorkerProfile.objects.count())
att_count = timeit('attestations count', lambda: Attestation.objects.count())
active_count = timeit('active count', lambda: Attestation.objects.filter(status='active').count())

print()
print("=" * 75)
print("TOTALS")
print(f"  featured_workers: {len(featured_workers)}")
print(f"  top_skills: {len(top_skills)}")
print(f"  workers: {workers_count}, attestations: {att_count}, active: {active_count}")