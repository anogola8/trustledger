"""Download DiceBear avatars locally for instant loading."""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import urllib.request
from pathlib import Path
from django.conf import settings
from workers.models import WorkerProfile
from accounts.models import User
import hashlib

CACHE_DIR = Path(settings.BASE_DIR) / 'static' / 'avatars'
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def avatar_path(name):
    seed = hashlib.md5(name.encode('utf-8'), usedforsecurity=False).hexdigest()[:12]
    return CACHE_DIR / f'{seed}.svg'

def download_avatar(name):
    path = avatar_path(name)
    if path.exists():
        return path
    seed = path.stem
    url = f'https://api.dicebear.com/7.x/avataaars/svg?seed={seed}&backgroundType=gradientLinear'
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            path.write_bytes(resp.read())
        return path
    except Exception as e:
        print(f'Failed to download avatar for {name}: {e}')
        return None

# Download for all workers
count = 0
for w in WorkerProfile.objects.all()[:500]:
    if download_avatar(w.full_name):
        count += 1
    if count % 50 == 0:
        print(f'Downloaded {count} avatars...')

print(f'✅ Cached {count} avatars locally')