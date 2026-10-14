import datetime

from django.test import Client, TestCase
from django.urls import reverse

from attestations import services

from .helpers import PW, make_employer, make_worker, signed_attestation


class SecurityTests(TestCase):
    def test_csrf_enforced_on_state_changes(self):
        w, e = make_worker(username='wk'), make_employer(username='em')
        att = services.create_attestation(e, w, 'Cook', '', datetime.date(2023, 1, 1), None)
        c = Client(enforce_csrf_checks=True)
        c.login(username='wk', password=PW)
        self.assertEqual(c.post(reverse('attestations:confirm', args=[att.pk])).status_code, 403)
        att.refresh_from_db()
        self.assertEqual(att.status, 'pending')

    def test_xss_is_escaped(self):
        w = make_worker('<script>alert(1)</script>', username='xss')
        signed_attestation(w, make_employer('<img src=x onerror=alert(1)>'), role='<b>boss</b>')
        r = self.client.get(reverse('workers:public', args=[w.slug]))
        body = r.content.decode()
        self.assertNotIn('<script>alert(1)</script>', body)
        self.assertNotIn('<img src=x', body)
        self.assertIn('&lt;b&gt;boss&lt;/b&gt;', body)

    def test_security_headers(self):
        r = self.client.get(reverse('core:landing'))
        self.assertIn("default-src 'self'", r['Content-Security-Policy'])
        self.assertEqual(r['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(r['X-Frame-Options'], 'DENY')

    def test_passwords_are_hashed(self):
        w = make_worker(username='h')
        self.assertNotIn(PW, w.user.password)
        self.assertTrue(w.user.password.startswith(('md5$', 'pbkdf2_sha256$')))

    def test_private_key_never_exposed(self):
        e = make_employer(username='k')
        w = make_worker(username='kw')
        att = signed_attestation(w, e)
        for url in [reverse('verification:result', args=[att.verification_code]), reverse('workers:public', args=[w.slug]),
                    f'/api/verify/{att.verification_code}/', '/api/workers/' + w.slug + '/']:
            self.assertNotContains(self.client.get(url), e.encrypted_private_key)
        c = Client()
        c.login(username='k', password=PW)
        self.assertNotIn(e.encrypted_private_key, c.get(reverse('dashboard:home')).content.decode())
        self.assertNotIn(e.encrypted_private_key, c.get('/api/employers/me/').content.decode())

    def test_verification_codes_are_unique_and_unguessable(self):
        codes = {signed_attestation(make_worker(f'W{i}', username=f'u{i}'), make_employer(f'E{i}', username=f'e{i}')).verification_code for i in range(15)}
        self.assertEqual(len(codes), 15)

    def test_open_redirect_not_possible_via_notifications(self):
        from notifications.models import Notification
        w = make_worker(username='nr')
        n = Notification.objects.create(user=w.user, message='x', url='')
        c = Client()
        c.login(username='nr', password=PW)
        self.assertEqual(c.post(reverse('notifications:read', args=[n.pk])).status_code, 302)

    def test_healthz(self):
        self.assertEqual(self.client.get('/healthz').json(), {'status': 'ok'})
