from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render


def landing(request):
    """Landing page with featured verified workers and platform stats."""
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    from workers.models import WorkerProfile, Skill
    from attestations.models import Attestation
    from django.db.models import Count, Q, Max

    featured_workers = (
        WorkerProfile.objects
        .annotate(
            active_count=Count('attestations', filter=Q(attestations__status='active')),
            latest_score=Max('trust_scores__value'),
        )
        .filter(active_count__gte=1, latest_score__isnull=False)
        .order_by('-latest_score', '-active_count')[:8]
    )

    top_skills = (
        Skill.objects.values('name')
        .annotate(n=Count('id'))
        .order_by('-n')[:12]
    )

    stats = {
        'workers': WorkerProfile.objects.count(),
        'attestations': Attestation.objects.count(),
        'active': Attestation.objects.filter(status='active').count(),
    }

    return render(request, 'core/landing.html', {
        'featured_workers': featured_workers,
        'top_skills': top_skills,
        'stats': stats,
    })


def healthz(request):
    with connection.cursor() as cur:
        cur.execute('SELECT 1')
    return JsonResponse({'status': 'ok'})