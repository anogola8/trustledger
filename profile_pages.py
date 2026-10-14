"""Profile all major pages — find N+1 queries and slow views."""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.test.utils import override_settings
from django.db import connection, reset_queries
from django.conf import settings
import time

settings.DEBUG = True

ANON_PAGES = [
    '/',
    '/workers/explore/',
    '/workers/explore/?skill=House%20Cleaning',
    '/workers/explore/?min_trust=60',
    '/verify/',
    '/accounts/login/',
    '/accounts/register/worker/',
]

AUTHED_PAGES = [
    '/dashboard/',
    '/workers/portfolio/',
    '/workers/timeline/',
    '/workers/profile/',
    '/attestations/',
    '/notifications/',
    '/disputes/',
]

with override_settings(ALLOWED_HOSTS=['testserver', 'localhost']):
    c = Client()

    print()
    print("=" * 85)
    print(f"{'URL':50} {'HTTP':>4} {'Queries':>8} {'DB ms':>8} {'Total ms':>8}")
    print("=" * 85)

    for url in ANON_PAGES:
        reset_queries()
        try:
            t0 = time.time()
            r = c.get(url)
            elapsed = (time.time() - t0) * 1000
            db_time = sum(float(q['time']) for q in connection.queries) * 1000
            n = len(connection.queries)
            flag = ''
            if n > 20:
                flag = ' ← N+1?'
            elif elapsed > 500:
                flag = ' ← SLOW'
            print(f"{url:50} {r.status_code:>4} {n:>8} {db_time:>8.1f} {elapsed:>8.1f}{flag}")
        except Exception as e:
            print(f"{url:50} ERROR: {e}")

    # Log in as a worker for authenticated pages
    from accounts.models import User
    u = User.objects.filter(role='worker').first()
    if u:
        c.force_login(u)
        print()
        print("Authed as:", u.email)
        print("-" * 85)
        for url in AUTHED_PAGES:
            reset_queries()
            try:
                t0 = time.time()
                r = c.get(url)
                elapsed = (time.time() - t0) * 1000
                db_time = sum(float(q['time']) for q in connection.queries) * 1000
                n = len(connection.queries)
                flag = ''
                if n > 20:
                    flag = ' ← N+1?'
                elif elapsed > 500:
                    flag = ' ← SLOW'
                print(f"{url:50} {r.status_code:>4} {n:>8} {db_time:>8.1f} {elapsed:>8.1f}{flag}")
            except Exception as e:
                print(f"{url:50} ERROR: {e}")

    # Admin pages
    admin = User.objects.filter(is_superuser=True).first()
    if admin:
        c.force_login(admin)
        print()
        print("Authed as:", admin.email, "(admin)")
        print("-" * 85)
        admin_pages = ['/dashboard/users/', '/dashboard/employers/', '/dashboard/flags/', '/dashboard/verifications/', '/audit/']
        for url in admin_pages:
            reset_queries()
            try:
                t0 = time.time()
                r = c.get(url)
                elapsed = (time.time() - t0) * 1000
                db_time = sum(float(q['time']) for q in connection.queries) * 1000
                n = len(connection.queries)
                flag = ''
                if n > 20:
                    flag = ' ← N+1?'
                elif elapsed > 500:
                    flag = ' ← SLOW'
                print(f"{url:50} {r.status_code:>4} {n:>8} {db_time:>8.1f} {elapsed:>8.1f}{flag}")
            except Exception as e:
                print(f"{url:50} ERROR: {e}")

print("=" * 85)