#!/usr/bin/env bash
# Render build script — runs on every deploy
set -o errexit  # exit on error

echo "==> Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Collecting static files..."
python manage.py collectstatic --no-input

echo "==> Running migrations..."
python manage.py migrate --no-input

echo "==> Checking if seed is needed..."
python manage.py shell -c "
from workers.models import WorkerProfile
from accounts.models import User

if WorkerProfile.objects.count() == 0:
    from django.core.management import call_command
    print('  Seeding demo data (this happens once)...')
    call_command('seed_big_demo', workers=100, employers=20)
    print('  Demo data seeded OK')
else:
    print(f'  Already have {WorkerProfile.objects.count()} workers - skipping seed')

if not User.objects.filter(email='demo.admin@trustledger.demo').exists():
    User.objects.create_superuser(
        username='demo_admin',
        email='demo.admin@trustledger.demo',
        password='Demo1234!',
        role='admin',
    )
    print('  Created demo.admin@trustledger.demo')
else:
    print('  Demo admin already exists')
"

echo "==> Build complete."