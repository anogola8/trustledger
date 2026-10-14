"""Builds the work experience timeline: verified (signed) entries plus clearly-labelled self-declared ones."""
from attestations.models import Attestation


def build_timeline(worker, include_pending=False):
    items = []
    statuses = [Attestation.Status.ACTIVE]
    for a in worker.attestations.filter(status__in=statuses).select_related('employer'):
        items.append({'kind': 'verified', 'title': a.role_title, 'org': a.employer.organisation_name,
                      'start': a.start_date, 'end': a.end_date, 'description': a.description,
                      'code': a.verification_code, 'status': a.status})
    for e in worker.experiences.all():
        items.append({'kind': 'declared', 'title': e.role_title, 'org': e.employer_name, 'start': e.start_date,
                      'end': e.end_date, 'description': e.description, 'code': '', 'status': 'self-declared'})
    items.sort(key=lambda i: i['start'], reverse=True)
    return items
