from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.views.decorators.http import require_GET
from django.shortcuts import get_object_or_404, redirect, render

from audit.services import log
from core.ratelimit import allow
from core.utils import hash_ip

from .forms import EmployerRegistrationForm, LoginForm, WorkerRegistrationForm
from .emails import send_verification_email
from .models import EmailVerification


class TrustLoginView(LoginView):
    form_class = LoginForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from workers.models import WorkerProfile
        from attestations.models import Attestation
        from django.db.models import Count, Q, Max

        ctx['stats'] = {
            'workers': WorkerProfile.objects.count(),
            'attestations': Attestation.objects.count(),
            'active': Attestation.objects.filter(status='active').count(),
        }
        ctx['featured_workers'] = list(
            WorkerProfile.objects
            .annotate(
                active_count=Count('attestations', filter=Q(attestations__status='active')),
                latest_score=Max('trust_scores__value'),
            )
            .filter(active_count__gte=1, latest_score__isnull=False)
            .order_by('-latest_score')[:5]
        )
        return ctx

    def post(self, request, *args, **kwargs):
        if not allow(f'login:{hash_ip(request)}', limit=10, window=60):
            messages.error(request, 'Too many attempts. Please wait a minute and try again.')
            return redirect('accounts:login')
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        log(form.get_user(), 'user.login', 'user', form.get_user().pk)
        return response


def _register(request, form_class, title, intro):
    form = form_class(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        log(user, 'user.register', 'user', user.pk, {'role': user.role})
        login(request, user)
        verification = EmailVerification.objects.create(user=user)
        send_verification_email(request, user, verification)
        messages.success(request, 'Welcome to TrustLedger! Check your email for the verification link.')
        return redirect('dashboard:home')
    return render(request, 'accounts/register.html', {'form': form, 'title': title, 'intro': intro})


def register_worker(request):
    return _register(request, WorkerRegistrationForm, 'Create a worker account',
                     'Build a portable, verifiable work history that you own.')


def register_employer(request):
    return _register(request, EmployerRegistrationForm, 'Create an employer account',
                     'Issue digitally signed work attestations. New employers are approved by an administrator before issuing.')


def verify_email(request, token):
    """Handle email verification link."""
    verification = get_object_or_404(EmailVerification, token=token)
    if verification.verified_at:
        messages.info(request, 'Your email is already verified.')
    elif not verification.is_valid():
        messages.error(request, 'This link has expired. Please request a new one.')
    else:
        verification.mark_verified()
        log(verification.user, 'user.email_verified', 'user', verification.user.pk)
        messages.success(request, '✅ Email verified. Thank you!')
    return redirect('dashboard:home')


def resend_verification(request):
    """Resend verification email. Accepts GET (direct link) and POST (banner form)."""
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    verification, _ = EmailVerification.objects.get_or_create(user=request.user)
    send_verification_email(request, request.user, verification)
    messages.info(request, f'Verification email sent to {request.user.email}.')
    return redirect('dashboard:home')