"""Standalone security test — bypasses ALLOWED_HOSTS for testing."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.test.utils import override_settings
from accounts.models import User
from attestations.models import Attestation
from verification.services import verify_code


print("=" * 60)
print("LIVE SECURITY TESTS (with testserver allowed)")
print("=" * 60)

with override_settings(ALLOWED_HOSTS=['testserver', 'localhost']):
    # 1. CSRF protection
    c = Client(enforce_csrf_checks=True)
    r = c.post('/attestations/issue/', {'role_title': 'hack'})
    print(f"1. CSRF: HTTP {r.status_code} {'✅ BLOCKED' if r.status_code == 403 else '❌ VULNERABLE'}")

    # 2. Unauth API
    c2 = Client()
    r = c2.get('/api/workers/me/')
    print(f"2. Unauth API: HTTP {r.status_code} {'✅ BLOCKED' if r.status_code in (401, 403) else '❌ VULNERABLE'}")

    # 3. SQL injection
    r = c2.get("/workers/explore/?q=' OR 1=1--")
    print(f"3. SQL injection: HTTP {r.status_code} {'✅ SAFE' if r.status_code == 200 else '❌ ERROR ' + str(r.status_code)}")

    # 4. XSS attempt
    r = c2.get("/workers/explore/?q=<script>alert('xss')</script>")
    xss = b'<script>alert' in r.content
    print(f"4. XSS: HTTP {r.status_code} {'❌ UNSAFE' if xss else '✅ SAFE — escaped'}")

    # 5. IDOR
    att = Attestation.objects.first()
    if att:
        other = User.objects.filter(role='worker').exclude(id=att.worker.user_id).first()
        if other:
            c3 = Client()
            c3.force_login(other)
            r = c3.get(f'/attestations/{att.id}/')
            print(f"5. IDOR: HTTP {r.status_code} {'✅ BLOCKED' if r.status_code == 403 else '⚠️  ' + str(r.status_code)}")

    # 6. Rate limit
    c4 = Client()
    blocked_at = None
    for i in range(15):
        r = c4.post('/accounts/login/', {'username': 'fake', 'password': 'fake'})
        if r.status_code == 429 or 'Too many' in str(r.content):
            blocked_at = i + 1
            break
    if blocked_at:
        print(f"6. Rate limit: ✅ Blocked after {blocked_at} attempts")
    else:
        print("6. Rate limit: ⚠️  Not detected in 15 attempts")

    # 7. Admin URL protection
    c5 = Client()
    r = c5.get('/admin/')
    print(f"7. Admin URL: HTTP {r.status_code} {'✅ REDIRECTS TO LOGIN' if r.status_code == 302 else '⚠️  ' + str(r.status_code)}")

    # 8. Password hashing
    u = User.objects.first()
    algo = u.password.split('$')[0]
    print(f"8. Password hash: {algo} {'✅ STRONG (PBKDF2)' if 'pbkdf2' in algo else '❌ WEAK'}")

    # 9. Signature tamper
    active = Attestation.objects.filter(status='active').first()
    if active:
        code = active.verification_code
        orig = active.role_title
        active.role_title = 'TAMPERED'
        active.save()
        res = verify_code(code)
        active.role_title = orig
        active.save()
        print(f"9. Signature tamper: result = {res.status} {'✅ DETECTED' if res.status != 'verified' else '❌ NOT DETECTED'}")

    # 10. HTTPS redirect (should be off in dev)
    print(f"10. SESSION_COOKIE_SECURE: {os.environ.get('DJANGO_SESSION_COOKIE_SECURE', 'False (dev)')}")

print("=" * 60)