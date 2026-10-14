"""TEMPORARY: One-time superuser creator. Delete after use."""
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import os


@csrf_exempt
def create_admin(request):
    """
    One-time superuser creation endpoint.
    Protected by SETUP_SECRET env var.
    Usage: /setup-admin/?secret=xxx&email=you@example.com&password=xxx
    """
    secret = request.GET.get('secret', '')
    expected = os.environ.get('SETUP_SECRET', '')

    if not expected or secret != expected:
        return HttpResponse("❌ Invalid or missing secret.", status=403)

    email = request.GET.get('email', '').strip()
    password = request.GET.get('password', '').strip()
    username = request.GET.get('username', email.split('@')[0] if email else '').strip()

    if not email or not password:
        return HttpResponse("❌ Provide ?email=...&password=...", status=400)

    if len(password) < 8:
        return HttpResponse("❌ Password must be at least 8 characters.", status=400)

    from accounts.models import User

    try:
        with transaction.atomic():
            user = User.objects.filter(email=email).first()
            if user:
                user.set_password(password)
                user.is_superuser = True
                user.is_staff = True
                user.role = 'admin'
                user.is_active = True
                user.save()
                action = "updated"
            else:
                user = User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password,
                    role='admin',
                )
                action = "created"

        return HttpResponse(
            f"✅ Superuser {action}: <b>{email}</b><br>"
            f"Username: {user.username}<br>"
            f"Login at <a href='/admin/'>/admin/</a><br><br>"
            f"⚠️ <b>Delete this URL immediately!</b> "
            f"Remove the SETUP_SECRET env var and redeploy."
        )
    except Exception as e:
        import traceback
        return HttpResponse(
            f"❌ Failed: {e}<br><pre>{traceback.format_exc()}</pre>",
            status=500,
        )