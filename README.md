# TrustLedger MVP

A Verifiable Digital Work-History and Reputation Management Platform for Informal and Gig Workers.
Employers issue **digitally signed (Ed25519) attestations**; workers confirm them and own a portable profile;
anyone verifies by **QR code / public page** without an account.

Stack: Django 5.2 · Django REST Framework · PostgreSQL (SQLite for quick local use) · Celery + Redis · Bootstrap 5 · Chart.js · ReportLab · Docker.

## Quick start (no Docker, SQLite)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

python manage.py migrate
python manage.py seed_demo    # demo admin / worker / employers and signed attestations
python manage.py runserver
```
Open http://localhost:8000. Demo logins (password `DemoPass#2026` unless `DEMO_PASSWORD` is set): `admin`, `amina` (worker), `njeri` / `sunrise` / `mamarosa` (employers). `seed_demo` prints verification codes to try at `/verify/`.

## Docker (PostgreSQL + Redis + Celery worker)
```bash
cp .env.example .env   # set SECRET_KEY and KEY_ENCRYPTION_KEY
docker compose up --build
docker compose exec web python manage.py seed_demo
```

## Tests
```bash
coverage run --source=. --omit='*/migrations/*,tests/*,manage.py,config/wsgi.py' manage.py test tests
coverage report --fail-under=80
```
79 tests, ~97% line coverage (unit, integration, security, API). CI: `.github/workflows/ci.yml` (runs on PostgreSQL).

## Apps
`accounts` users & roles · `workers` profile, skills, certificates, timeline, CV · `employers` profile, approval, signing keys, ratings ·
`attestations` issue → consent → sign → revoke · `verification` public verify, QR, PDF report · `trustscore` score, badges, fraud rules ·
`disputes` · `notifications` · `audit` hash-chained log · `dashboard` role dashboards & admin tools · `core` shared utilities, landing, API router.

## Key environment variables
| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django secret (required when `DEBUG=0`) |
| `KEY_ENCRYPTION_KEY` | Fernet key that encrypts issuer private keys at rest (required when `DEBUG=0`) |
| `DATABASE_URL` | PostgreSQL URL (defaults to SQLite) |
| `CELERY_BROKER_URL` | Redis URL. **If empty, Celery tasks run inline** (used on free hosting without a worker) |
| `SITE_URL` | Public base URL used inside QR codes and PDFs |
| `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` | Comma-separated lists |

Generate a Fernet key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
**Back up `KEY_ENCRYPTION_KEY`**: without it issuer signing keys cannot be decrypted.

## Deploying on Render (free)
Use `render.yaml`. Free-tier facts to plan for (verify on Render's docs before relying on them): web services sleep after ~15 minutes idle;
free Render Postgres expires after 30 days, so use a free external PostgreSQL via `DATABASE_URL`; free plans have no background worker, so leave
`CELERY_BROKER_URL` empty; the free disk is ephemeral, so uploaded files do not survive redeploys (move to object storage for production).

## Security notes
PBKDF2 password hashing, CSRF on all forms, template auto-escaping and a Content-Security-Policy, role-based access control on every view and API route,
private storage for certificates/evidence, hashed IPs, throttled verification and login, secure random verification codes, tamper-evident audit log.
A digital signature proves who signed and that nothing changed; it cannot prove the statement is true.
