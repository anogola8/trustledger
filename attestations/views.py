from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.permissions import role_required
from employers.forms import RatingForm
from employers.models import EmployerRating

from .forms import IssueAttestationForm, ReasonForm
from .models import Attestation
from . import services
from .services import ServiceError


def _can_view(user, att):
    return user.is_admin_role or (user.is_worker and att.worker.user_id == user.id) or \
        (user.is_employer and att.employer.user_id == user.id)


@role_required('worker', 'employer', 'admin')
def attestation_list(request):
    u = request.user
    if u.is_worker:
        qs = Attestation.objects.filter(worker=u.worker_profile).select_related('employer')
    elif u.is_employer:
        qs = Attestation.objects.filter(employer=u.employer_profile).select_related('worker')
    else:
        qs = Attestation.objects.select_related('worker', 'employer')
    status = request.GET.get('status')
    if status:
        qs = qs.filter(status=status)
    return render(request, 'attestations/list.html', {'items': qs[:200], 'statuses': Attestation.Status.choices, 'status': status})


@role_required('employer')
def issue(request):
    emp = request.user.employer_profile
    if not emp.can_issue:
        messages.warning(request, 'Your organisation is awaiting administrator approval. You can issue attestations once approved.')
        return redirect('dashboard:home')
    form = IssueAttestationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            att = services.create_attestation(emp, form.worker, form.cleaned_data['role_title'], form.cleaned_data['description'],
                                              form.cleaned_data['start_date'], form.cleaned_data['end_date'])
        except ServiceError as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, 'Attestation sent to the worker for confirmation.')
            return redirect('attestations:detail', pk=att.pk)
    return render(request, 'form.html', {'form': form, 'title': 'Issue an attestation', 'back': 'dashboard:home',
                                         'intro': 'The worker must confirm before the record is digitally signed.'})


@role_required('worker', 'employer', 'admin')
def detail(request, pk):
    att = get_object_or_404(Attestation.objects.select_related('worker', 'employer'), pk=pk)
    if not _can_view(request.user, att):
        raise PermissionDenied
    rating = getattr(att, 'rating', None)
    return render(request, 'attestations/detail.html', {
        'att': att, 'rating': rating, 'reason_form': ReasonForm(),
        'is_owner_worker': request.user.is_worker and att.worker.user_id == request.user.id,
        'is_owner_employer': request.user.is_employer and att.employer.user_id == request.user.id})


def _action(request, pk, fn, success, *args):
    att = get_object_or_404(Attestation.objects.select_related('worker', 'employer'), pk=pk)
    try:
        fn(att, request.user, *args)
        messages.success(request, success)
    except ServiceError as exc:
        messages.error(request, str(exc))
    return redirect('attestations:detail', pk=pk)


@role_required('worker')
@require_POST
def confirm(request, pk):
    return _action(request, pk, services.confirm, 'Confirmed. The attestation has been digitally signed.')


@role_required('worker')
@require_POST
def reject(request, pk):
    return _action(request, pk, services.reject, 'Attestation rejected.')


@role_required('employer', 'admin')
@require_POST
def revoke(request, pk):
    form = ReasonForm(request.POST)
    reason = form.cleaned_data['reason'] if form.is_valid() else ''
    return _action(request, pk, services.revoke, 'Attestation revoked.', reason)


@role_required('employer')
def rate(request, pk):
    att = get_object_or_404(Attestation, pk=pk, employer=request.user.employer_profile)
    if att.status != Attestation.Status.ACTIVE:
        messages.error(request, 'Only active, signed attestations can be rated.')
        return redirect('attestations:detail', pk=pk)
    instance = getattr(att, 'rating', None)
    form = RatingForm(request.POST or None, instance=instance)
    if request.method == 'POST' and form.is_valid():
        r = form.save(commit=False)
        r.attestation, r.employer, r.worker = att, att.employer, att.worker
        r.save()
        from audit.services import log
        from core.tasks_util import dispatch
        from trustscore.tasks import recompute_trust_score
        log(request.user, 'attestation.rate', 'attestation', att.id, {'score': r.score})
        dispatch(recompute_trust_score, att.worker_id)
        messages.success(request, 'Rating saved.')
        return redirect('attestations:detail', pk=pk)
    return render(request, 'form.html', {'form': form, 'title': f'Rate {att.worker.full_name}', 'back': 'attestations:list'})
