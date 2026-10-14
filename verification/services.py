from dataclasses import dataclass

from attestations import crypto
from attestations.models import Attestation
from attestations.services import build_payload
from core.utils import normalise_code

from .models import VerificationRequest


@dataclass
class Result:
    status: str          # verified | revoked | disputed | invalid | not_found
    attestation: object = None
    reason: str = ''

    @property
    def ok(self):
        return self.status == 'verified'


def verify_code(raw_code):
    """Recompute the hash from the stored facts and validate the Ed25519 signature."""
    code = normalise_code(raw_code)
    try:
        att = Attestation.objects.select_related('worker', 'employer', 'signature').get(verification_code=code)
    except Attestation.DoesNotExist:
        return Result('not_found', reason='No attestation matches this code.')
    sig = getattr(att, 'signature', None)
    if sig is None or not att.confirmed_at:
        return Result('invalid', att, 'The record has no digital signature.')
    expected = crypto.hash_payload(build_payload(att, att.confirmed_at.isoformat(), sig.key_id))
    if expected != att.payload_hash:
        return Result('invalid', att, 'The record does not match what was signed (possible tampering).')
    if sig.key_id != att.employer.key_id or not crypto.verify_signature(att.employer.public_key, sig.signature, att.payload_hash):
        return Result('invalid', att, 'The digital signature could not be validated.')
    if att.status == Attestation.Status.REVOKED:
        return Result('revoked', att, att.revoked_reason or 'This attestation was revoked by the issuer.')
    if att.status == Attestation.Status.DISPUTED:
        return Result('disputed', att, 'This attestation is under dispute review.')
    if not att.employer.can_issue:
        return Result('invalid', att, 'The issuing organisation is not currently in good standing.')
    return Result('verified', att)


def verify_and_log(raw_code, method, ip_hash):
    result = verify_code(raw_code)
    VerificationRequest.objects.create(attestation=result.attestation, code_queried=normalise_code(raw_code)[:30],
                                       method=method, result=result.status, ip_hash=ip_hash)
    return result
