"""Print all demo credentials in a clean format."""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User
from workers.models import WorkerProfile
from employers.models import EmployerProfile
from attestations.models import Attestation
from trustscore.models import TrustScore

DEMO_PW = 'Demo1234!'

print()
print("=" * 78)
print(" TRUSTLEDGER — DEMO CREDENTIALS")
print("=" * 78)
print()

# ---------- ADMINS ----------
print("👑 ADMINS (superuser — password is what YOU set)")
print("-" * 78)
for u in User.objects.filter(role='admin').order_by('email'):
    superuser = " [superuser]" if u.is_superuser else ""
    print(f"  {u.email}{superuser}")
print()

# ---------- EMPLOYERS (approved) ----------
print("🏢 EMPLOYERS — Approved (password: Demo1234!)")
print("-" * 78)
emp_list = EmployerProfile.objects.filter(status='approved').select_related('user').order_by('organisation_name')[:10]
for e in emp_list:
    n_atts = e.attestations.count()
    print(f"  {e.user.email:42} | {e.organisation_name:30} | {n_atts:3} attestations")
print()

# ---------- EMPLOYERS (pending) ----------
pending = EmployerProfile.objects.filter(status='pending')[:5]
if pending.exists():
    print("🏢 EMPLOYERS — Pending Approval (password: Demo1234!)")
    print("-" * 78)
    for e in pending:
        print(f"  {e.user.email:42} | {e.organisation_name}")
    print()

# ---------- WORKERS (rich data — for demo) ----------
print("🧑 WORKERS — Top by Trust Score (password: Demo1234!)")
print("-" * 78)
workers = (
    WorkerProfile.objects
    .select_related('user')
    .order_by('-trust_scores__value')[:10]
)
seen = set()
for w in workers:
    if w.id in seen:
        continue
    seen.add(w.id)
    ts = TrustScore.objects.filter(worker=w).order_by('-computed_at').first()
    score = f"{ts.value:.0f}" if ts else "—"
    n_active = w.attestations.filter(status='active').count()
    print(f"  {w.user.email:42} | {w.full_name:22} | Trust: {score:>3} | {n_active} verified | slug: {w.slug}")
print()

# ---------- VERIFICATION CODES ----------
print("🔐 VERIFICATION CODES — for /verify/<code>/ (sample)")
print("-" * 78)
codes = Attestation.objects.filter(status='active').select_related('worker', 'employer').order_by('-confirmed_at')[:8]
for a in codes:
    print(f"  {a.verification_code}  →  {a.worker.full_name} ({a.role_title} at {a.employer.organisation_name})")
print()

# ---------- PUBLIC PORTFOLIOS ----------
print("🌐 PUBLIC PORTFOLIOS — for /w/<slug>/portfolio/ (no login)")
print("-" * 78)
pub = WorkerProfile.objects.filter(attestations__status='active').distinct()[:6]
for w in pub:
    print(f"  http://127.0.0.1:8000/w/{w.slug}/portfolio/")
print()

# ---------- KEY URLS ----------
print("🔗 KEY URLS")
print("-" * 78)
urls = [
    ("Landing page", "http://127.0.0.1:8000/"),
    ("Explore workers", "http://127.0.0.1:8000/workers/explore/"),
    ("Verify portal", "http://127.0.0.1:8000/verify/"),
    ("Login", "http://127.0.0.1:8000/accounts/login/"),
    ("Worker register", "http://127.0.0.1:8000/accounts/register/worker/"),
    ("Employer register", "http://127.0.0.1:8000/accounts/register/employer/"),
    ("Password reset", "http://127.0.0.1:8000/accounts/password-reset/"),
    ("Django admin", "http://127.0.0.1:8000/admin/"),
]
for label, url in urls:
    print(f"  {label:22} → {url}")
print()

print("=" * 78)
print(f" Remember: demo password for @trustledger.demo accounts is: {DEMO_PW}")
print("=" * 78)
print()