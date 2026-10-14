import hashlib
import secrets

from django.conf import settings

CODE_ALPHABET = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'  # no 0/O/1/I/L confusion


def new_verification_code():
    raw = ''.join(secrets.choice(CODE_ALPHABET) for _ in range(10))
    return f'TL-{raw[:5]}-{raw[5:]}'


def normalise_code(code):
    return (code or '').strip().upper().replace(' ', '')


def client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def hash_ip(request):
    """IPs are never stored in the clear (data minimisation)."""
    return hashlib.sha256(f'{settings.SECRET_KEY}|{client_ip(request)}'.encode()).hexdigest()


def absolute_url(path):
    return f'{settings.SITE_URL}{path}'
