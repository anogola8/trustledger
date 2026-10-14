from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from audit.services import log
from core.pdf import Paragraph, Spacer, build_pdf, qr_flowable, qr_png_bytes, table
from core.permissions import role_required
from core.utils import absolute_url
from trustscore.models import TrustScore, WorkerBadge

from .forms import CertificateForm, ExperienceForm, SkillForm, WorkerProfileForm
from .models import Certificate, Skill, WorkerProfile, WorkExperience
from .timeline import build_timeline


def _worker(request):
    return request.user.worker_profile


@role_required('worker')
def manage(request):
    w = _worker(request)
    return render(request, 'workers/manage.html', {
        'worker': w, 'skills': w.skills.all(), 'certs': w.certificates.all(), 'experiences': w.experiences.all(),
        'skill_form': SkillForm(worker=w), 'exp_form': ExperienceForm(), 'cert_form': CertificateForm(),
        'public_url': absolute_url(w.get_absolute_url())})


@role_required('worker')
def edit_profile(request):
    w = _worker(request)
    form = WorkerProfileForm(request.POST or None, request.FILES or None, instance=w)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log(request.user, 'worker.profile_update', 'worker', w.pk)
        messages.success(request, 'Profile updated.')
        return redirect('workers:manage')
    return render(request, 'form.html', {'form': form, 'title': 'Edit profile', 'multipart': True, 'back': 'workers:manage'})


def _add(request, form_class, title, save, **kw):
    form = form_class(request.POST or None, request.FILES or None, **kw)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.worker = _worker(request)
        obj.save()
        save(obj)
        messages.success(request, f'{title} saved.')
        return redirect('workers:manage')
    return render(request, 'form.html', {'form': form, 'title': title, 'multipart': True, 'back': 'workers:manage'})


@role_required('worker')
def add_skill(request):
    return _add(request, SkillForm, 'Add skill', lambda o: None, worker=_worker(request))


@role_required('worker')
def add_certificate(request):
    return _add(request, CertificateForm, 'Upload certificate', lambda o: log(request.user, 'worker.certificate_add', 'certificate', o.pk))


@role_required('worker')
def add_experience(request):
    return _add(request, ExperienceForm, 'Add self-declared experience', lambda o: None)


def _delete(request, model, pk, label):
    obj = get_object_or_404(model, pk=pk, worker=_worker(request))
    obj.delete()
    messages.info(request, f'{label} removed.')
    return redirect('workers:manage')


@role_required('worker')
@require_POST
def delete_skill(request, pk):
    return _delete(request, Skill, pk, 'Skill')


@role_required('worker')
@require_POST
def delete_certificate(request, pk):
    return _delete(request, Certificate, pk, 'Certificate')


@role_required('worker')
@require_POST
def delete_experience(request, pk):
    return _delete(request, WorkExperience, pk, 'Experience')


@login_required
def certificate_file(request, pk):
    """Certificates are private: only the owner and administrators may open them."""
    cert = get_object_or_404(Certificate, pk=pk)
    if not (request.user.is_admin_role or (request.user.is_worker and cert.worker.user_id == request.user.id)):
        raise PermissionDenied
    try:
        return FileResponse(cert.file.open('rb'), as_attachment=False)
    except FileNotFoundError:
        raise Http404


@role_required('worker')
def timeline(request):
    return render(request, 'workers/timeline.html', {'items': build_timeline(_worker(request)), 'worker': _worker(request)})


def public_profile(request, slug):
    w = get_object_or_404(WorkerProfile, slug=slug, user__is_active=True)
    score = TrustScore.objects.filter(worker=w).order_by('-computed_at', '-id').first()
    return render(request, 'workers/public.html', {
        'w': w, 'items': build_timeline(w), 'score': score, 'badges': w.badges.all(),
        'skills': w.skills.all() if w.show_skills else [],
        'certs': w.certificates.all() if w.show_certificates else [],
        'public_url': absolute_url(w.get_absolute_url())})


def profile_qr(request, slug):
    w = get_object_or_404(WorkerProfile, slug=slug)
    resp = HttpResponse(qr_png_bytes(absolute_url(w.get_absolute_url())), content_type='image/png')
    if request.GET.get('download'):
        resp['Content-Disposition'] = f'attachment; filename="trustledger-{w.slug}.png"'
    return resp


@role_required('worker')
def cv_pdf(request):
    w = _worker(request)
    score = TrustScore.objects.filter(worker=w).order_by('-computed_at', '-id').first()
    items = build_timeline(w)
    url = absolute_url(w.get_absolute_url())

    def story(st):
        s = [Paragraph(w.full_name, st['title'])]
        if w.headline:
            s.append(Paragraph(w.headline, st['body']))
        s.append(Paragraph(f'{w.location or ""} &nbsp; Trust score: {score.value if score else "n/a"}/100', st['small']))
        s.append(Spacer(1, 6))
        if w.bio:
            s += [Paragraph('Profile', st['h2']), Paragraph(w.bio, st['body'])]
        s.append(Paragraph('Verified experience (digitally signed)', st['h2']))
        rows = [['Role', 'Employer', 'Period', 'Code']]
        for i in items:
            if i['kind'] == 'verified':
                rows.append([i['title'], i['org'], f"{i['start']:%b %Y} - {i['end']:%b %Y}" if i['end'] else f"{i['start']:%b %Y} - present", i['code']])
        s.append(table(rows, [45 * 2.83, 55 * 2.83, 40 * 2.83, 40 * 2.83]) if len(rows) > 1 else Paragraph('No verified experience yet.', st['body']))
        decl = [i for i in items if i['kind'] == 'declared']
        if decl:
            s.append(Paragraph('Self-declared experience (not verified)', st['h2']))
            s.append(table([['Role', 'Employer', 'Period']] + [[i['title'], i['org'], f"{i['start']:%b %Y} - {i['end']:%b %Y}" if i['end'] else f"{i['start']:%b %Y} - present"] for i in decl]))
        if w.skills.exists():
            s += [Paragraph('Skills (self-declared)', st['h2']), Paragraph(', '.join(f'{k.name} ({k.get_level_display()})' for k in w.skills.all()), st['body'])]
        if w.certificates.exists():
            s += [Paragraph('Certificates (self-declared)', st['h2']), Paragraph('; '.join(c.title for c in w.certificates.all()), st['body'])]
        s += [Spacer(1, 10), qr_flowable(url), Paragraph(f'Scan or visit {url} to verify this CV against signed records.', st['small'])]
        return s

    resp = HttpResponse(build_pdf(story), content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="cv-{w.slug}.pdf"'
    return resp



# ============================================================
# PORTFOLIO VIEWS
# ============================================================

@role_required('worker')
def portfolio(request):
    """Worker's own curated portfolio view (login required)."""
    w = _worker(request)
    timeline_items = build_timeline(w)
    active_atts = w.attestations.filter(status='active').select_related('employer')
    pending_atts = w.attestations.filter(status='pending').select_related('employer')
    latest_score = TrustScore.objects.filter(worker=w).order_by('-computed_at').first()
    badges = w.badges.all()

    skills_by_cat = {'Skills': list(w.skills.all())}
    certs = w.certificates.all()

    return render(request, 'workers/portfolio.html', {
        'worker': w,
        'timeline': timeline_items,
        'active_atts': active_atts,
        'pending_atts': pending_atts,
        'latest_score': latest_score,
        'badges': badges,
        'skills_by_cat': skills_by_cat,
        'certificates': certs,
        'public_url': absolute_url(w.get_absolute_url()),
        'is_public': False,
    })


def portfolio_public(request, slug):
    """Public portfolio - no login required."""
    w = get_object_or_404(WorkerProfile, slug=slug)
    timeline_items = build_timeline(w)
    active_atts = w.attestations.filter(status='active').select_related('employer')
    latest_score = TrustScore.objects.filter(worker=w).order_by('-computed_at').first()
    badges = w.badges.all()

    skills_by_cat = {'Skills': list(w.skills.all())}
    certs = w.certificates.all()

    return render(request, 'workers/portfolio.html', {
        'worker': w,
        'timeline': timeline_items,
        'active_atts': active_atts,
        'pending_atts': [],
        'latest_score': latest_score,
        'badges': badges,
        'skills_by_cat': skills_by_cat,
        'certificates': certs,
        'public_url': absolute_url(w.get_absolute_url()),
        'is_public': True,
    })

# ============================================================
# WORKER DISCOVERY / EXPLORE
# ============================================================

def explore(request):
    """Public worker discovery page with search + filters."""
    from django.core.paginator import Paginator
    from django.db.models import Count, Q, Max

    qs = WorkerProfile.objects.select_related('user').annotate(
        active_count=Count('attestations', filter=Q(attestations__status='active')),
        latest_score=Max('trust_scores__value'),
    )

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(full_name__icontains=q) |
            Q(headline__icontains=q) |
            Q(location__icontains=q) |
            Q(skills__name__icontains=q)
        ).distinct()

    skill = request.GET.get('skill', '').strip()
    if skill:
        qs = qs.filter(skills__name=skill)

    loc = request.GET.get('location', '').strip()
    if loc:
        qs = qs.filter(location__icontains=loc)

    min_trust = request.GET.get('min_trust', '')
    if min_trust and min_trust.isdigit():
        qs = qs.filter(latest_score__gte=int(min_trust))

    min_verified = request.GET.get('min_verified', '')
    if min_verified and min_verified.isdigit():
        qs = qs.filter(active_count__gte=int(min_verified))

    sort = request.GET.get('sort', 'trust')
    if sort == 'name':
        qs = qs.order_by('full_name')
    elif sort == 'recent':
        qs = qs.order_by('-created_at')
    elif sort == 'verified':
        qs = qs.order_by('-active_count', '-latest_score')
    else:
        qs = qs.order_by('-latest_score', '-active_count', 'full_name')

    qs = qs.filter(latest_score__isnull=False)

    all_skills = Skill.objects.values_list('name', flat=True).distinct().order_by('name')
    all_locations = (WorkerProfile.objects
                     .exclude(location='')
                     .values_list('location', flat=True)
                     .distinct().order_by('location'))

    paginator = Paginator(qs, 24)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'workers/explore.html', {
        'page': page,
        'total': paginator.count,
        'q': q,
        'skill': skill,
        'location': loc,
        'min_trust': min_trust,
        'min_verified': min_verified,
        'sort': sort,
        'all_skills': all_skills,
        'all_locations': all_locations,
    })