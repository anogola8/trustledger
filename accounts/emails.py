"""Email helpers for account-related notifications."""
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags


def send_verification_email(request, user, verification):
    """Send the email verification link. Prints to console in dev."""
    verify_url = request.build_absolute_uri(
        reverse('accounts:verify_email', kwargs={'token': str(verification.token)})
    )
    html = render_to_string('accounts/emails/verify_email.html', {
        'user': user,
        'verify_url': verify_url,
    })
    send_mail(
        subject='Verify your TrustLedger email',
        message=strip_tags(html),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html,
        fail_silently=True,
    )