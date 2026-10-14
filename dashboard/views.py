import datetime

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from attestations.models import Attestation
from audit.services import log
from core.permissions import role_required
from core.utils import absolute_url
from disputes.models import Dispute
from employers.models import EmployerProfile
from notifications.services import notify
from trustscore.models import FraudFlag, TrustScore
from verification.models import VerificationRequest

User = get_user_model()


@role_required('worker', 'employer', 'admin')
def home(request):
    u = request.user
    if u.is_worker:
        return worker_dashboard(request)
    if u.is_employer:
        return employer_dashboard(request)
    return admin_dashboard(request)


def _daily(qs, field, days=14):
    since = timezone.now() - datetime.timedelta(days=days)
    rows = qs.filter(**{f'{field}__gte': since}).annotate(d=TruncDate(field)).values('d').annotate(n=Count('id')).order_by('d')
    return {'labels': [r['d'].isoformat() for r in rows], 'values': [r['n'] for r in rows]}


def worker_dashboard(request):
    w = request.user.worker_profile
    scores = list(TrustScore.objects.filter(worker=w).order_by('computed_at', 'id')[:30])
    latest = scores[-1] if scores else None
    ver = VerificationRequest.objects.filter(attestation__worker=w)
    atts = w.attestations
    ctx = {
        'w': w, 'latest': latest, 'badges': w.badges.all(), 'pending': atts.filter(status='pending').select_related('employer'), 'active_attestations': atts.filter(status='active').select_related('employer').order_by('-start_date'),
        'active_count': atts.filter(status='active').count(), 'verifications_total': ver.count(),
        'verified_ok': ver.filter(result='verified').count(), 'public_url': absolute_url(w.get_absolute_url()),
        'trend': {'labels': [s.computed_at.strftime('%d %b') for s in scores], 'values': [float(s.value) for s in scores]},
        'daily': _daily(ver, 'created_at'),
        'open_disputes': Dispute.objects.filter(attestation__worker=w, status='open').count(),
    }
    return render(request, 'dashboard/worker.html', ctx)


def employer_dashboard(request):
    e = request.user.employer_profile
    atts = e.attestations
    by_status = {r['status']: r['n'] for r in atts.values('status').annotate(n=Count('id'))}
    labels = [label for key, label in Attestation.Status.choices]
    ctx = {'e': e, 'by_status': by_status, 'total': atts.count(),
           'chart': {'labels': labels, 'values': [by_status.get(k, 0) for k, _ in Attestation.Status.choices]},
           'recent': atts.select_related('worker')[:8],
           'verifications': VerificationRequest.objects.filter(attestation__employer=e).count(),
           'daily': _daily(VerificationRequest.objects.filter(attestation__employer=e), 'created_at')}
    return render(request, 'dashboard/employer.html', ctx)


def admin_dashboard(request):
    ver = VerificationRequest.objects.all()
    results = {r['result']: r['n'] for r in ver.values('result').annotate(n=Count('id'))}
    ctx = {
        'users': User.objects.count(), 'workers': User.objects.filter(role='worker').count(),
        'employers': User.objects.filter(role='employer').count(),
        'pending_employers': EmployerProfile.objects.filter(status='pending').select_related('user'),
        'open_disputes': Dispute.objects.filter(status='open').count(), 'open_flags': FraudFlag.objects.filter(status='open').count(),
        'attestations': Attestation.objects.count(), 'verifications': ver.count(),
        'chart_results': {'labels': list(results.keys()), 'values': list(results.values())},
        'daily': _daily(ver, 'created_at'),
    }
    return render(request, 'dashboard/admin.html', ctx)


@role_required('admin')
def users(request):
    qs = User.objects.order_by('-date_joined')
    role, q = request.GET.get('role', ''), request.GET.get('q', '').strip()
    if role:
        qs = qs.filter(role=role)
    if q:
        qs = qs.filter(username__icontains=q) | qs.filter(email__icontains=q)
    return render(request, 'dashboard/users.html', {'page': Paginator(qs, 25).get_page(request.GET.get('page')), 'role': role, 'q': q, 'roles': ['worker', 'employer', 'admin']})


@role_required('admin')
@require_POST
def toggle_user(request, pk):
    target = get_object_or_404(User, pk=pk)
    if target.pk == request.user.pk:
        messages.error(request, 'You cannot deactivate your own account.')
    else:
        target.is_active = not target.is_active
        target.save(update_fields=['is_active'])
        log(request.user, 'admin.user_toggle', 'user', target.pk, {'active': target.is_active})
        messages.success(request, f'{target.username} is now {"active" if target.is_active else "deactivated"}.')
    return redirect('dashboard:users')


@role_required('admin')
def employers(request):
    return render(request, 'dashboard/employers.html', {'items': EmployerProfile.objects.select_related('user').order_by('status', 'organisation_name')})


@role_required('admin')
@require_POST
def employer_action(request, pk, action):
    emp = get_object_or_404(EmployerProfile, pk=pk)
    if action == 'approve':
        emp.approve()
        notify(emp.user, 'Your organisation has been approved. You can now issue attestations.', '/attestations/issue/')
    elif action == 'suspend':
        emp.suspend()
        notify(emp.user, 'Your organisation has been suspended. Contact the administrator.', '')
    else:
        messages.error(request, 'Unknown action.')
        return redirect('dashboard:employers')
    log(request.user, f'admin.employer_{action}', 'employer', emp.pk)
    messages.success(request, f'{emp.organisation_name}: {action} done.')
    return redirect('dashboard:employers')


@role_required('admin')
def verifications(request):
    qs = VerificationRequest.objects.select_related('attestation__worker')
    result = request.GET.get('result', '')
    if result:
        qs = qs.filter(result=result)
    return render(request, 'dashboard/verifications.html', {'page': Paginator(qs, 30).get_page(request.GET.get('page')), 'result': result, 'results': ['verified', 'revoked', 'disputed', 'invalid', 'not_found']})


@role_required('admin')
def flags(request):
    qs = FraudFlag.objects.select_related('attestation__worker', 'employer')
    status = request.GET.get('status', 'open')
    if status:
        qs = qs.filter(status=status)
    return render(request, 'dashboard/flags.html', {'items': qs[:200], 'status': status, 'statuses': ['open', 'cleared', 'confirmed']})


@role_required('admin')
@require_POST
def flag_action(request, pk, action):
    flag = get_object_or_404(FraudFlag, pk=pk)
    if action not in ('cleared', 'confirmed'):
        messages.error(request, 'Unknown action.')
        return redirect('dashboard:flags')
    flag.status, flag.reviewed_by, flag.reviewed_at = action, request.user, timezone.now()
    flag.save()
    log(request.user, 'admin.flag_review', 'fraud_flag', flag.pk, {'status': action})
    if flag.attestation_id:
        from core.tasks_util import dispatch
        from trustscore.tasks import recompute_trust_score
        dispatch(recompute_trust_score, flag.attestation.worker_id)
    messages.success(request, f'Flag marked {action}.')
    return redirect('dashboard:flags')
