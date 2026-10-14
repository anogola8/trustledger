from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from attestations.models import Attestation
from attestations.services import ServiceError
from core.permissions import role_required

from . import services
from .forms import DisputeForm, ResolveForm
from .models import Dispute


def _can_view(user, d):
    a = d.attestation
    return user.is_admin_role or a.worker.user_id == user.id or a.employer.user_id == user.id


@role_required('worker', 'employer', 'admin')
def dispute_list(request):
    u = request.user
    qs = Dispute.objects.select_related('attestation__worker', 'attestation__employer')
    if u.is_worker:
        qs = qs.filter(attestation__worker=u.worker_profile)
    elif u.is_employer:
        qs = qs.filter(attestation__employer=u.employer_profile)
    return render(request, 'disputes/list.html', {'items': qs[:200]})


@role_required('worker', 'employer')
def new_dispute(request, att_id):
    att = get_object_or_404(Attestation.objects.select_related('worker', 'employer'), pk=att_id)
    if not services.can_raise(request.user, att):
        raise PermissionDenied
    form = DisputeForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        try:
            d = services.open_dispute(att, request.user, form.cleaned_data['reason'], form.cleaned_data.get('evidence'))
        except ServiceError as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, 'Dispute submitted. An administrator will review it.')
            return redirect('disputes:detail', pk=d.pk)
    return render(request, 'form.html', {'form': form, 'title': 'Raise a dispute', 'multipart': True,
                                         'back': 'attestations:list', 'intro': f'Attestation: {att.role_title} ({att.worker.full_name})'})


@role_required('worker', 'employer', 'admin')
def detail(request, pk):
    d = get_object_or_404(Dispute.objects.select_related('attestation__worker', 'attestation__employer', 'raised_by'), pk=pk)
    if not _can_view(request.user, d):
        raise PermissionDenied
    return render(request, 'disputes/detail.html', {'d': d, 'form': ResolveForm()})


@role_required('worker', 'employer', 'admin')
def evidence(request, pk):
    d = get_object_or_404(Dispute, pk=pk)
    if not _can_view(request.user, d) or not d.evidence:
        raise PermissionDenied
    try:
        return FileResponse(d.evidence.open('rb'))
    except FileNotFoundError:
        raise Http404


@role_required('admin')
@require_POST
def resolve(request, pk):
    d = get_object_or_404(Dispute, pk=pk)
    form = ResolveForm(request.POST)
    if form.is_valid():
        try:
            services.resolve(d, request.user, form.cleaned_data['decision'], form.cleaned_data['note'])
            messages.success(request, 'Dispute resolved.')
        except ServiceError as exc:
            messages.error(request, str(exc))
    else:
        messages.error(request, 'Please choose a decision and write a note.')
    return redirect('disputes:detail', pk=pk)
