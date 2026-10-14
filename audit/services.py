import hashlib
import json

from django.db import transaction
from django.utils import timezone

from .models import AuditLog

GENESIS = '0' * 64


def _digest(prev_hash, actor_id, action, entity_type, entity_id, details, created_at):
    body = '|'.join([prev_hash, str(actor_id or ''), action, entity_type, str(entity_id),
                     json.dumps(details, sort_keys=True, default=str), created_at.isoformat()])
    return hashlib.sha256(body.encode()).hexdigest()


def log(actor, action, entity_type='', entity_id='', details=None):
    details = details or {}
    with transaction.atomic():
        last = AuditLog.objects.order_by('-id').first()
        prev = last.entry_hash if last else GENESIS
        now = timezone.now()
        actor = actor if (actor is not None and getattr(actor, 'pk', None)) else None
        entry = AuditLog(actor=actor, action=action, entity_type=entity_type, entity_id=str(entity_id),
                         details=details, created_at=now, prev_hash=prev)
        entry.entry_hash = _digest(prev, actor.pk if actor else '', action, entity_type, str(entity_id), details, now)
        entry.save()
    return entry


def verify_chain():
    """Returns (ok, first_bad_id). Detects edited, deleted or re-ordered entries."""
    prev = GENESIS
    for e in AuditLog.objects.order_by('id'):
        expected = _digest(prev, e.actor_id, e.action, e.entity_type, e.entity_id, e.details, e.created_at)
        if e.prev_hash != prev or e.entry_hash != expected:
            return False, e.id
        prev = e.entry_hash
    return True, None
