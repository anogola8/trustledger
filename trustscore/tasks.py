from celery import shared_task

from attestations.models import Attestation
from workers.models import WorkerProfile

from . import services


@shared_task
def recompute_trust_score(worker_id):
    worker = WorkerProfile.objects.filter(pk=worker_id).first()
    if worker:
        return str(services.recompute(worker).value)


@shared_task
def run_fraud_checks(attestation_id):
    att = Attestation.objects.select_related('employer', 'worker').filter(pk=attestation_id).first()
    if not att:
        return 0
    flags = services.evaluate_attestation(att)
    return len(flags)
