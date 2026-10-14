import datetime

from django.test import TestCase
from rest_framework.test import APIClient

from attestations.models import Attestation

from .helpers import PW, make_admin, make_employer, make_worker, signed_attestation


class APITests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()  # reset DRF throttles between tests
        self.c = APIClient()
        self.w, self.e, self.admin = make_worker(username='wk'), make_employer(username='em'), make_admin()

    def auth(self, username):
        r = APIClient().post('/api/auth/login/', {'username': username, 'password': PW}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Token ' + r.json()['token'])
        return c

    def test_register_login_me_logout(self):
        r = self.c.post('/api/auth/register/', {'role': 'worker', 'username': 'api1', 'email': 'a1@x.co', 'password': PW, 'full_name': 'Api One'}, format='json')
        self.assertEqual(r.status_code, 201)
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION='Token ' + r.json()['token'])
        self.assertEqual(c.get('/api/auth/me/').json()['role'], 'worker')
        self.assertEqual(c.post('/api/auth/logout/').status_code, 204)
        self.assertEqual(c.get('/api/auth/me/').status_code, 401)
        r = self.c.post('/api/auth/register/', {'role': 'employer', 'username': 'api2', 'email': 'a2@x.co', 'password': PW, 'organisation_name': 'Api Org'}, format='json')
        self.assertEqual(r.status_code, 201)

    def test_register_validation(self):
        bad = [{'role': 'worker', 'username': 'wk', 'email': 'z@x.co', 'password': PW, 'full_name': 'X'},
               {'role': 'worker', 'username': 'q1', 'email': 'wk@x.co', 'password': PW, 'full_name': 'X'},
               {'role': 'worker', 'username': 'q2', 'email': 'q2@x.co', 'password': '12345678', 'full_name': 'X'},
               {'role': 'worker', 'username': 'q3', 'email': 'q3@x.co', 'password': PW},
               {'role': 'employer', 'username': 'q4', 'email': 'q4@x.co', 'password': PW},
               {'role': 'admin', 'username': 'q5', 'email': 'q5@x.co', 'password': PW}]
        for b in bad:
            self.assertEqual(self.c.post('/api/auth/register/', b, format='json').status_code, 400, b)

    def test_login_failure(self):
        self.assertEqual(self.c.post('/api/auth/login/', {'username': 'wk', 'password': 'bad'}, format='json').status_code, 400)

    def test_profiles(self):
        c = self.auth('wk')
        self.assertEqual(c.get('/api/workers/me/').json()['full_name'], 'Amina Wanjiru')
        self.assertEqual(c.patch('/api/workers/me/', {'headline': 'Cook'}, format='json').json()['headline'], 'Cook')
        self.assertEqual(c.post('/api/workers/me/skills/', {'name': 'Baking', 'level': 2, 'years': 3}, format='json').status_code, 201)
        self.assertEqual(c.post('/api/workers/me/skills/', {'name': 'baking', 'level': 2, 'years': 3}, format='json').status_code, 400)
        self.assertEqual(len(c.get('/api/workers/me/skills/').json()), 1)
        self.assertEqual(self.auth('em').get('/api/workers/me/').status_code, 403)
        ec = self.auth('em')
        self.assertEqual(ec.patch('/api/employers/me/', {'description': 'We hire'}, format='json').status_code, 200)
        self.assertEqual(c.get('/api/employers/me/').status_code, 403)

    def test_public_worker_and_trust_score(self):
        signed_attestation(self.w, self.e)
        r = self.c.get(f'/api/workers/{self.w.slug}/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()['verified_experience']), 1)
        t = self.c.get(f'/api/workers/{self.w.slug}/trust-score/').json()
        self.assertGreater(t['score'], 0)
        self.assertIn('A', t['components'])
        self.assertEqual(self.c.get('/api/workers/nope/').status_code, 404)

    def test_attestation_api_flow(self):
        ec, wc = self.auth('em'), self.auth('wk')
        body = {'worker': self.w.slug, 'role_title': 'Driver', 'description': 'x', 'start_date': '2023-01-01'}
        r = ec.post('/api/attestations/', body, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        aid = r.json()['id']
        self.assertEqual(wc.post('/api/attestations/', body, format='json').status_code, 403)
        self.assertEqual(ec.post('/api/attestations/', {**body, 'end_date': '2022-01-01'}, format='json').status_code, 400)
        self.assertEqual(wc.get(f'/api/attestations/{aid}/').status_code, 200)
        self.assertEqual(wc.post(f'/api/attestations/{aid}/revoke/', {'reason': 'x'}, format='json').status_code, 400)
        r = wc.post(f'/api/attestations/{aid}/confirm/')
        self.assertEqual(r.json()['status'], 'active')
        code = r.json()['verification_code']
        self.assertEqual(wc.post(f'/api/attestations/{aid}/confirm/').status_code, 400)
        self.assertEqual(len(wc.get('/api/attestations/').json()['results']), 1)
        self.assertEqual(len(ec.get('/api/attestations/').json()['results']), 1)
        self.assertEqual(len(self.auth('boss').get('/api/attestations/').json()['results']), 1)
        v = self.c.get(f'/api/verify/{code}/').json()
        self.assertTrue(v['valid'])
        self.assertEqual(v['attestation']['algorithm'], 'Ed25519')
        outsider = make_worker('Out', username='outs')
        self.assertEqual(self.auth('outs').get(f'/api/attestations/{aid}/').status_code, 403)
        self.assertEqual(ec.post(f'/api/attestations/{aid}/revoke/', {'reason': 'Mistake'}, format='json').json()['status'], 'revoked')
        self.assertEqual(self.c.get(f'/api/verify/{code}/').json()['status'], 'revoked')
        self.assertEqual(self.c.get('/api/verify/TL-NOPE0-NOPE0/').status_code, 404)
        r2 = ec.post('/api/attestations/', body, format='json').json()['id']
        self.assertEqual(wc.post(f'/api/attestations/{r2}/reject/').json()['status'], 'rejected')

    def test_unauthenticated_blocked(self):
        for path in ['/api/attestations/', '/api/auth/me/', '/api/disputes/', '/api/notifications/', '/api/workers/me/']:
            self.assertEqual(self.c.get(path).status_code, 401, path)

    def test_disputes_and_notifications_api(self):
        a = signed_attestation(self.w, self.e)
        wc, adm = self.auth('wk'), self.auth('boss')
        self.assertEqual(wc.post('/api/disputes/', {'attestation': str(a.id)}, format='json').status_code, 400)
        r = wc.post('/api/disputes/', {'attestation': str(a.id), 'reason': 'Wrong dates'}, format='json')
        self.assertEqual(r.status_code, 201)
        did = r.json()['id']
        self.assertEqual(wc.post('/api/disputes/', {'attestation': str(a.id), 'reason': 'again'}, format='json').status_code, 403)
        self.assertEqual(len(wc.get('/api/disputes/').json()['results']), 1)
        self.assertEqual(len(self.auth('em').get('/api/disputes/').json()['results']), 1)
        self.assertEqual(len(adm.get('/api/disputes/').json()['results']), 1)
        self.assertEqual(wc.post(f'/api/disputes/{did}/resolve/', {'decision': 'uphold', 'note': 'x'}, format='json').status_code, 403)
        self.assertEqual(adm.post(f'/api/disputes/{did}/resolve/', {'decision': 'bad', 'note': 'x'}, format='json').status_code, 400)
        self.assertEqual(adm.post(f'/api/disputes/{did}/resolve/', {'decision': 'uphold', 'note': 'ok'}, format='json').json()['status'], 'upheld')
        n = adm.get('/api/notifications/').json()['results']
        self.assertTrue(n)
        self.assertTrue(adm.post(f'/api/notifications/{n[0]["id"]}/read/').json()['is_read'])
        self.assertEqual(adm.post('/api/notifications/999999/read/').status_code, 404)

    def test_admin_employer_endpoints(self):
        pend = make_employer('Pend', approved=False, username='pp')
        adm = self.auth('boss')
        self.assertGreaterEqual(len(adm.get('/api/employers/').json()['results']), 2)
        self.assertEqual(adm.post(f'/api/employers/{pend.pk}/approve/').json()['status'], 'approved')
        self.assertEqual(self.auth('wk').get('/api/employers/').status_code, 403)
        self.assertEqual(self.auth('wk').post(f'/api/employers/{pend.pk}/approve/').status_code, 403)
