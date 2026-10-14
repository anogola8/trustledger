"""Explainable trust score, badges and fraud rules."""
import datetime
import math
from decimal import Decimal

from django.db.models import Avg, Count
from django.utils import timezone

from attestations.models import Attestation
from employers.models import EmployerRating

from .models import FraudFlag, TrustScore, WorkerBadge

WEIGHTS = {'A': 0.30, 'T': 0.20, 'I': 0.20, 'R': 0.15, 'Q': 0.15}
PENALTY_PER_HIGH_FLAG, MAX_PENALTY = 10, 30

BADGES = {
    'FIRST_VERIFIED': {'label': 'First Verified Job', 'description': 'Has at least one signed, active attestation.'},
    'MULTI_EMPLOYER': {'label': 'Trusted by Many', 'description': 'Verified by three or more different employers.'},
    'VETERAN': {'label': 'Experienced', 'description': 'Two or more years of verified work.'},
    'TOP_RATED': {'label': 'Top Rated', 'description': 'Average rating of 4.5 or more from at least three ratings.'},
    'CLEAN_RECORD': {'label': 'Clean Record', 'description': 'Three or more verified jobs and no confirmed fraud flags.'},
}


def _months_covered(attestations, today):
    """Length of the union of all verified date ranges, in months."""
    spans = sorted((a.start_date, a.end_date or today) for a in attestations)
    total, cur_s, cur_e = 0, None, None
    for s, e in spans:
        if cur_e is None or s > cur_e:
            if cur_e is not None:
                total += (cur_e - cur_s).days
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    if cur_e is not None:
        total += (cur_e - cur_s).days
    return total / 30.44


def compute_components(worker, today=None):
    today = today or datetime.date.today()
    active = list(worker.attestations.filter(status=Attestation.Status.ACTIVE))
    n = len(active)
    A = 1 - math.exp(-n / 5)
    T = min(1.0, _months_covered(active, today) / 36)
    I = min(1.0, len({a.employer_id for a in active}) / 5)
    recent_cut = today - datetime.timedelta(days=730)
    R = (sum(1 for a in active if a.end_date is None or a.end_date >= recent_cut) / n) if n else 0.0
    avg = EmployerRating.objects.filter(attestation__in=active).aggregate(a=Avg('score'))['a']
    Q = (avg / 5) if avg else 0.0
    high_flags = FraudFlag.objects.filter(attestation__worker=worker, severity='high', status__in=['open', 'confirmed']).count()
    F = min(MAX_PENALTY, PENALTY_PER_HIGH_FLAG * high_flags)
    return {'A': round(A, 4), 'T': round(T, 4), 'I': round(I, 4), 'R': round(R, 4), 'Q': round(Q, 4), 'F': F,
            'active_attestations': n, 'employers': len({a.employer_id for a in active}), 'avg_rating': round(avg, 2) if avg else None}


def score_from_components(c):
    raw = 100 * sum(WEIGHTS[k] * c[k] for k in WEIGHTS) - c['F']
    return Decimal(str(round(max(0.0, min(100.0, raw)), 2)))


def recompute(worker):
    comps = compute_components(worker)
    score = TrustScore.objects.create(worker=worker, value=score_from_components(comps), components=comps)
    award_badges(worker, comps)
    return score


def award_badges(worker, comps=None):
    comps = comps or compute_components(worker)
    earned = set()
    n, emps = comps['active_attestations'], comps['employers']
    if n >= 1:
        earned.add('FIRST_VERIFIED')
    if emps >= 3:
        earned.add('MULTI_EMPLOYER')
    if comps['T'] >= 24 / 36:
        earned.add('VETERAN')
    ratings = EmployerRating.objects.filter(worker=worker, attestation__status='active')
    agg = ratings.aggregate(a=Avg('score'), c=Count('id'))
    if agg['c'] >= 3 and (agg['a'] or 0) >= 4.5:
        earned.add('TOP_RATED')
    if n >= 3 and not FraudFlag.objects.filter(attestation__worker=worker, status='confirmed').exists():
        earned.add('CLEAN_RECORD')
    for code in earned:
        WorkerBadge.objects.get_or_create(worker=worker, code=code)
    WorkerBadge.objects.filter(worker=worker).exclude(code__in=earned).delete()
    return earned


# ---------------- Fraud monitoring rules ----------------

def _flag(rule, severity, reason, attestation=None, employer=None):
    exists = FraudFlag.objects.filter(rule_code=rule, attestation=attestation, employer=employer, status='open').exists()
    if exists:
        return None
    return FraudFlag.objects.create(rule_code=rule, severity=severity, reason=reason[:300], attestation=attestation, employer=employer)


def _overlap_days(a_start, a_end, b_start, b_end, today):
    s, e = max(a_start, b_start), min(a_end or today, b_end or today)
    return max(0, (e - s).days)


def evaluate_attestation(att, now=None, today=None):
    """Runs rules R1-R5 and returns the list of newly created flags."""
    now = now or timezone.now()
    today = today or datetime.date.today()
    emp, flags = att.employer, []
    # R1 burst issuance
    recent = Attestation.objects.filter(employer=emp, created_at__gte=now - datetime.timedelta(hours=24)).count()
    if recent > 10:
        flags.append(_flag('R1', 'medium', f'{emp.organisation_name} created {recent} attestations in 24 hours.', att))
    # R2 new employer surge
    if emp.approved_at and emp.approved_at >= now - datetime.timedelta(days=7) and emp.attestations.count() > 5:
        flags.append(_flag('R2', 'high', f'Recently approved employer issued {emp.attestations.count()} attestations in its first week.', att))
    # R3 overlapping full-time engagements from different employers
    for other in Attestation.objects.filter(worker=att.worker).exclude(pk=att.pk).exclude(employer=emp).exclude(status__in=['rejected', 'revoked']):
        days = _overlap_days(att.start_date, att.end_date, other.start_date, other.end_date, today)
        if days > 180:
            flags.append(_flag('R3', 'medium', f'Overlaps {days} days with an attestation from {other.employer.organisation_name}.', att))
            break
    # R4 duplicate descriptions across workers
    if len(att.description) >= 20:
        dup = Attestation.objects.filter(employer=emp, description=att.description).values('worker').distinct().count()
        if dup >= 3:
            flags.append(_flag('R4', 'low', 'The same description was used for three or more different workers.', att))
    # R5 uniform top ratings
    ratings = list(EmployerRating.objects.filter(employer=emp).values_list('score', flat=True))
    if len(ratings) >= 5 and all(r == 5 for r in ratings):
        flags.append(_flag('R5', 'low', f'{emp.organisation_name} gave the top rating in all {len(ratings)} ratings.', employer=emp))
    return [f for f in flags if f]
