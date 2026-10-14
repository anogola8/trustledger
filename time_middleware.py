"""Time the middleware chain to find the slow step."""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import time
from django.test import Client
from django.test.utils import override_settings
from django.db import connection, reset_queries
from django.conf import settings
settings.DEBUG = True

with override_settings(ALLOWED_HOSTS=['testserver', 'localhost'], DEBUG=False):
    c = Client()

    print("=" * 70)
    print("MIDDLEWARE PHASE TIMING — / (landing)")
    print("=" * 70)

    for i in range(5):
        reset_queries()
        t0 = time.time()
        r = c.get('/')
        elapsed = (time.time() - t0) * 1000
        n = len(connection.queries)
        db_time = sum(float(q['time']) for q in connection.queries) * 1000
        print(f"Call {i+1}: {elapsed:8.1f} ms  ({n} queries, {db_time:.1f} ms DB)")

    # Now profile a similar view (explore) for comparison
    print()
    print("=" * 70)
    print("COMPARISON — /workers/explore/")
    print("=" * 70)
    for i in range(5):
        reset_queries()
        t0 = time.time()
        r = c.get('/workers/explore/')
        elapsed = (time.time() - t0) * 1000
        n = len(connection.queries)
        db_time = sum(float(q['time']) for q in connection.queries) * 1000
        print(f"Call {i+1}: {elapsed:8.1f} ms  ({n} queries, {db_time:.1f} ms DB)")

print("=" * 70)