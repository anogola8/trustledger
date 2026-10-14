from django.db import transaction
from django.utils import timezone

from attestations.models import Attestation
from attestations.services import ServiceError, _after_change
from audit.services import log
from notifications.services import notify

from .models import Dispute


def can_raise(user, att):
    return (user.is_worker and att.worker.user_id == user.id) or (user.is_employer and att.employer.user_id == user.id)


@transaction.atomic
def open_dispute(att, user, reason, evidence=None):
    if not can_raise(user, att):
        raise ServiceError('Only the worker or the issuing employer can dispute this attestation.')
    if att.status != Attestation.Status.ACTIVE:
        raise ServiceError('Only active attestations can be disputed.')
    d = Dispute.objects.create(attestation=att, raised_by=user, reason=reason.strip(), evidence=evidence or '')
    att.status = Attestation.Status.DISPUTED
    att.save(update_fields=['status'])
    log(user, 'dispute.open', 'dispute', d.pk, {'attestation': str(att.id)})
    other = att.employer.user if user.is_worker else att.worker.user
    notify(other, 'A dispute was raised on an attestation you are part of.', f'/disputes/{d.pk}/')
    from django.contrib.auth import get_user_model
    for admin in get_user_model().objects.filter(role='admin', is_active=True)[:20]:
        notify(admin, f'New dispute #{d.pk} needs review.', f'/disputes/{d.pk}/')
    _after_change(att)
    return d


@transaction.atomic
def resolve(dispute, admin_user, decision, note):
    if not admin_user.is_admin_role:
        raise ServiceError('Only administrators can resolve disputes.')
    if dispute.status != Dispute.Status.OPEN:
        raise ServiceError('This dispute is already resolved.')
    if decision not in ('uphold', 'revoke'):
        raise ServiceError('Choose a valid decision.')
    att = dispute.attestation
    if decision == 'uphold':
        att.status, dispute.status = Attestation.Status.ACTIVE, Dispute.Status.UPHELD
    else:
        att.status, dispute.status = Attestation.Status.REVOKED, Dispute.Status.REVOKED
        att.revoked_at, att.revoked_reason = timezone.now(), f'Dispute #{dispute.pk}: {note[:200]}'
    att.save()
    dispute.decision_note, dispute.resolved_by, dispute.resolved_at = note.strip(), admin_user, timezone.now()
    dispute.save()
    log(admin_user, 'dispute.resolve', 'dispute', dispute.pk, {'decision': decision})
    for u in (att.worker.user, att.employer.user):
        notify(u, f'Dispute #{dispute.pk} was resolved: {dispute.get_status_display()}.', f'/disputes/{dispute.pk}/')
    _after_change(att)
    return dispute
