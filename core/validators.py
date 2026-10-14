import os

from django.conf import settings
from django.core.exceptions import ValidationError

ALLOWED_DOC_EXT = {'.pdf', '.jpg', '.jpeg', '.png'}
ALLOWED_IMG_EXT = {'.jpg', '.jpeg', '.png'}


def _check(file, allowed):
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in allowed:
        raise ValidationError(f'Unsupported file type. Allowed: {", ".join(sorted(allowed))}')
    if file.size > settings.MAX_UPLOAD_BYTES:
        raise ValidationError('File is too large (maximum 5 MB).')


def validate_document(file):
    _check(file, ALLOWED_DOC_EXT)


def validate_image(file):
    _check(file, ALLOWED_IMG_EXT)
