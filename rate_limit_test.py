import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.test.utils import override_settings

with override_settings(ALLOWED_HOSTS=['testserver', 'localhost']):
    c = Client()
    print("=" * 50)
    print("RATE LIMIT TEST — 15 login attempts")
    print("=" * 50)
    for i in range(15):
        r = c.post('/accounts/login/', {'username': 'fake@test.com', 'password': 'wrong'})
        marker = ''
        if r.status_code == 429:
            marker = ' ← ✅ THROTTLED'
        elif r.status_code == 302 and i >= 10:
            marker = ' ← might be redirect to error page'
        print(f"Attempt {i+1:2d}: HTTP {r.status_code}{marker}")

    # Direct check of the ratelimit module
    print()
    print("=" * 50)
    print("DIRECT LIMITER CHECK")
    print("=" * 50)
    try:
        from core.ratelimit import allow
        from core.utils import hash_ip
        # Simulate 10+ attempts for the same key
        for i in range(12):
            result = allow('login:test-ip', limit=10, window=60)
            if not result:
                print(f"Attempt {i+1}: ❌ DENIED — limiter works!")
                break
            print(f"Attempt {i+1}: ✅ allowed")
    except Exception as e:
        print(f"Error: {e}")

    print("=" * 50)