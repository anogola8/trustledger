"""Tests for the email verification flow."""
from datetime import timedelta

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import EmailVerification, User


class EmailVerificationTests(TestCase):
    def _register(self, email='new@test.com', username='newuser'):
        return self.client.post(reverse('accounts:register_worker'), {
            'username': username,
            'email': email,
            'phone': '0712345678',
            'full_name': 'New Worker',
            'password1': 'str0ng-Passw0rd-XYZ',
            'password2': 'str0ng-Passw0rd-XYZ',
        })

    def test_registration_creates_verification_record(self):
        response = self._register()
        # Sanity: ensure registration succeeded (302 redirect)
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email='new@test.com')
        self.assertTrue(EmailVerification.objects.filter(user=user).exists())
        self.assertFalse(user.is_email_verified)

    def test_registration_sends_email(self):
        self._register()
        self.assertGreaterEqual(len(mail.outbox), 1)
        email = mail.outbox[-1]
        self.assertIn('Verify', email.subject)

    def test_verify_token_marks_verified(self):
        self._register()
        user = User.objects.get(email='new@test.com')
        token = EmailVerification.objects.get(user=user).token

        self.client.logout()
        response = self.client.get(reverse('accounts:verify_email', args=[str(token)]))
        self.assertEqual(response.status_code, 302)

        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)

    def test_expired_token_rejected(self):
        self._register()
        user = User.objects.get(email='new@test.com')
        verification = EmailVerification.objects.get(user=user)
        verification.created_at = timezone.now() - timedelta(days=10)
        verification.save()

        self.client.logout()
        response = self.client.get(reverse('accounts:verify_email', args=[str(verification.token)]))
        self.assertEqual(response.status_code, 302)

        user.refresh_from_db()
        self.assertFalse(user.is_email_verified)

    def test_verify_invalid_uuid_404(self):
        import uuid
        response = self.client.get(reverse('accounts:verify_email', args=[str(uuid.uuid4())]))
        self.assertEqual(response.status_code, 404)

    def test_resend_verification_requires_login(self):
        response = self.client.post(reverse('accounts:resend_verification'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_resend_verification_sends_new_email(self):
        self._register()
        initial_count = len(mail.outbox)

        response = self.client.post(reverse('accounts:resend_verification'))
        self.assertEqual(response.status_code, 302)
        self.assertGreater(len(mail.outbox), initial_count)

    def test_email_verification_is_one_per_user(self):
        self._register()
        user = User.objects.get(email='new@test.com')
        self.assertEqual(EmailVerification.objects.filter(user=user).count(), 1)

        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            EmailVerification.objects.create(user=user)