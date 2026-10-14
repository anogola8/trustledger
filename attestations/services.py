"""Attestation workflow: issue -> worker consent -> sign -> (dispute | revoke)."""
from django.db import transaction
from django.utils import timezone

from audit.services import log
from core.tasks_util import dispatch
from core.utils import new_verification_code
from notifications.services import notify

from . import crypto
from .models import Attestation, AttestationSignature


class ServiceError(Exception):
    """A business-rule violation that is safe to show to the user."""


def build_payload(att, issued_at, key_id):
    """Only immutable identifiers and the attested facts are signed."""
    return {
        'v': 1, 'id': str(att.id), 'worker': att.worker.slug, 'employer': att.employer_id, 'key_id': key_id,
        'role': att.role_title, 'description': att.description,
        'start': att.start_date.isoformat(), 'end': att.end_date.isoformat() if att.end_date else None,
        'issued_at': issued_at,
    }


@transaction.atomic
def create_attestation(employer, worker, role_title, description, start_date, end_date):
    if not employer.can_issue:
        raise ServiceError('Your organisation must be approved before you can issue attestations.')
    att = Attestation.objects.create(worker=worker, employer=employer, role_title=role_title.strip(),
                                     description=description.strip(), start_date=start_date, end_date=end_date)
    log(employer.user, 'attestation.create', 'attestation', att.id, {'worker': worker.slug})
    notify(worker.user, f'{employer.organisation_name} wants to attest your work as "{att.role_title}". Please review.',
           f'/attestations/{att.id}/')
    from trustscore.tasks import run_fraud_checks
    dispatch(run_fraud_checks, str(att.id))
    return att


@transaction.atomic
def confirm(att, user):
    att = Attestation.objects.select_for_update().select_related('employer', 'worker').get(pk=att.pk)
    if att.worker.user_id != user.id:
        raise ServiceError('Only the worker named in the attestation can confirm it.')
    if att.status != Attestation.Status.PENDING:
        raise ServiceError('This attestation is not awaiting confirmation.')
    emp = att.employer
    if not emp.can_issue:
        raise ServiceError('The issuing organisation is not currently approved to sign attestations.')
    now = timezone.now()
    payload = crypto_payload = build_payload(att, now.isoformat(), emp.key_id)
    payload_hash = crypto.hash_payload(crypto_payload)
    signature = crypto.sign_hash(emp.encrypted_private_key, payload_hash)
    att.payload_hash = payload_hash
    att.verification_code = new_verification_code()
    att.confirmed_at = now
    att.status = Attestation.Status.ACTIVE
    att.save()
    AttestationSignature.objects.create(attestation=att, signature=signature, key_id=emp.key_id, signed_at=now)
    log(user, 'attestation.confirm_sign', 'attestation', att.id, {'code': att.verification_code, 'key_id': emp.key_id})
    notify(emp.user, f'{att.worker.full_name} confirmed your attestation. It is now signed.', f'/attestations/{att.id}/')
    _after_change(att)
    return att


@transaction.atomic
def reject(att, user):
    if att.worker.user_id != user.id:
        raise ServiceError('Only the worker named in the attestation can reject it.')
    if att.status != Attestation.Status.PENDING:
        raise ServiceError('This attestation is not awaiting confirmation.')
    att.status = Attestation.Status.REJECTED
    att.save(update_fields=['status'])
    log(user, 'attestation.reject', 'attestation', att.id)
    notify(att.employer.user, f'{att.worker.full_name} rejected your attestation request.', f'/attestations/{att.id}/')
    return att


@transaction.atomic
def revoke(att, user, reason):
    allowed = user.is_admin_role or (user.is_employer and att.employer.user_id == user.id)
    if not allowed:
        raise ServiceError('You are not allowed to revoke this attestation.')
    if att.status not in (Attestation.Status.ACTIVE, Attestation.Status.DISPUTED):
        raise ServiceError('Only signed attestations can be revoked.')
    if not reason.strip():
        raise ServiceError('Please give a reason for the revocation.')
    att.status = Attestation.Status.REVOKED
    att.revoked_at = timezone.now()
    att.revoked_reason = reason.strip()[:300]
    att.save(update_fields=['status', 'revoked_at', 'revoked_reason'])
    log(user, 'attestation.revoke', 'attestation', att.id, {'reason': att.revoked_reason})
    notify(att.worker.user, f'An attestation from {att.employer.organisation_name} was revoked.', f'/attestations/{att.id}/')
    _after_change(att)
    return att


def _after_change(att):
    from trustscore.tasks import recompute_trust_score
    dispatch(recompute_trust_score, att.worker_id)
