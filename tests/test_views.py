import datetime
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from attestations import services
from attestations.models import Attestation
from audit.services import verify_chain
from disputes import services as dsvc
from disputes.models import Dispute
from employers.models import EmployerProfile
from notifications.models import Notification
from trustscore.models import FraudFlag
from workers.models import Certificate, Skill, WorkExperience

from .helpers import PW, make_admin, make_employer, make_worker, signed_attestation


class PublicAndAuthTests(TestCase):
    def test_public_pages(self):
        for name in ['core:landing', 'accounts:login', 'accounts:register_worker', 'accounts:register_employer', 'verification:home', 'core:healthz']:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_register_worker_and_employer(self):
        r = self.client.post(reverse('accounts:register_worker'), {'username': 'newbie', 'email': 'n@x.co', 'phone': '0700', 'full_name': 'New Bie', 'password1': PW, 'password2': PW})
        self.assertRedirects(r, reverse('dashboard:home'), fetch_redirect_response=False)
        self.client.post(reverse('accounts:logout'))
        r = self.client.post(reverse('accounts:register_employer'), {'username': 'org1', 'email': 'o@x.co', 'phone': '', 'organisation_name': 'Org One', 'password1': PW, 'password2': PW})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(EmployerProfile.objects.get(user__username='org1').status, 'pending')

    def test_register_validation(self):
        make_worker('Dup', username='dup')
        r = self.client.post(reverse('accounts:register_worker'), {'username': 'x', 'email': 'dup@x.co', 'full_name': 'X', 'password1': PW, 'password2': 'other'})
        self.assertContains(r, 'already exists')
        self.assertContains(r, 'do not match')
        r = self.client.post(reverse('accounts:register_worker'), {'username': 'y', 'email': 'y@x.co', 'full_name': 'Y', 'password1': '12345678', 'password2': '12345678'})
        self.assertEqual(r.status_code, 200)

    def test_login_logout_and_throttle(self):
        w = make_worker(username='lg')
        self.assertTrue(self.client.login(username='lg', password=PW))
        self.assertEqual(self.client.get(reverse('accounts:login')).status_code, 302)
        self.client.post(reverse('accounts:logout'))
        from django.core.cache import cache
        cache.clear()
        r = self.client.post(reverse('accounts:login'), {'username': 'lg', 'password': PW})
        self.assertEqual(r.status_code, 302)
        self.client.post(reverse('accounts:logout'))
        for _ in range(11):
            r = self.client.post(reverse('accounts:login'), {'username': 'lg', 'password': 'wrong'})
        self.assertEqual(r.status_code, 302)  # throttled -> redirected with message
        cache.clear()


class RBACTests(TestCase):
    def setUp(self):
        self.w, self.e, self.admin = make_worker(username='wk'), make_employer(username='em'), make_admin()
        self.att = signed_attestation(self.w, self.e)

    def login(self, u):
        self.client.logout()
        self.client.login(username=u, password=PW)

    def test_anonymous_redirected_to_login(self):
        for name in ['dashboard:home', 'workers:manage', 'attestations:list', 'attestations:issue', 'disputes:list', 'notifications:list', 'audit:list']:
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 302, name)
            self.assertIn('/accounts/login/', r['Location'])

    def test_worker_cannot_access_employer_or_admin_pages(self):
        self.login('wk')
        for name in ['attestations:issue', 'employers:edit', 'employers:verify_worker', 'dashboard:users', 'dashboard:employers', 'dashboard:flags', 'dashboard:verifications', 'audit:list']:
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)

    def test_employer_cannot_access_worker_or_admin_pages(self):
        self.login('em')
        for name in ['workers:manage', 'workers:timeline', 'workers:cv', 'dashboard:users', 'audit:list']:
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)

    def test_cannot_view_others_attestation(self):
        outsider = make_worker('Out Sider', username='outs')
        self.login('outs')
        self.assertEqual(self.client.get(reverse('attestations:detail', args=[self.att.pk])).status_code, 403)
        make_employer('Other Org', username='oo')
        self.login('oo')
        self.assertEqual(self.client.get(reverse('attestations:detail', args=[self.att.pk])).status_code, 403)

    def test_dashboards_for_each_role(self):
        for u in ['wk', 'em', 'boss']:
            self.login(u)
            r = self.client.get(reverse('dashboard:home'))
            self.assertEqual(r.status_code, 200, u)
        self.login('wk')
        self.assertContains(self.client.get(reverse('dashboard:home')), 'Trust Score')

    def test_certificate_privacy(self):
        tmp = tempfile.mkdtemp()
        try:
            with override_settings(PRIVATE_ROOT=tmp):
                cert = Certificate.objects.create(worker=self.w, title='Cert', file=SimpleUploadedFile('c.pdf', b'%PDF-1.4 x'))
                self.login('wk')
                self.assertEqual(self.client.get(reverse('workers:certificate_file', args=[cert.pk])).status_code, 200)
                self.login('em')
                self.assertEqual(self.client.get(reverse('workers:certificate_file', args=[cert.pk])).status_code, 403)
                self.login('boss')
                self.assertEqual(self.client.get(reverse('workers:certificate_file', args=[cert.pk])).status_code, 200)
                self.client.logout()
                self.assertEqual(self.client.get(reverse('workers:certificate_file', args=[cert.pk])).status_code, 302)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class WorkerFeatureTests(TestCase):
    def setUp(self):
        self.w = make_worker(username='wk')
        self.client.login(username='wk', password=PW)

    def test_profile_edit_and_manage(self):
        r = self.client.post(reverse('workers:edit'), {'full_name': 'Amina W', 'headline': 'Cook', 'bio': 'hello', 'location': 'Meru', 'show_skills': 'on'})
        self.assertEqual(r.status_code, 302)
        self.w.refresh_from_db()
        self.assertEqual(self.w.headline, 'Cook')
        self.assertContains(self.client.get(reverse('workers:manage')), 'Skills portfolio')
        self.assertEqual(self.client.get(reverse('workers:edit')).status_code, 200)

    def test_skills_certificates_experience(self):
        self.client.post(reverse('workers:add_skill'), {'name': 'Cooking', 'level': 3, 'years': 5})
        self.assertEqual(Skill.objects.count(), 1)
        r = self.client.post(reverse('workers:add_skill'), {'name': 'cooking', 'level': 1, 'years': 1})
        self.assertContains(r, 'already listed')
        tmp = tempfile.mkdtemp()
        try:
            with override_settings(PRIVATE_ROOT=tmp):
                self.client.post(reverse('workers:add_certificate'), {'title': 'First aid', 'issuing_body': 'Red Cross', 'year': 2020, 'file': SimpleUploadedFile('a.pdf', b'%PDF')})
                self.assertEqual(Certificate.objects.count(), 1)
                bad = self.client.post(reverse('workers:add_certificate'), {'title': 'Bad', 'file': SimpleUploadedFile('a.exe', b'MZ')})
                self.assertContains(bad, 'Unsupported file type')
                big = self.client.post(reverse('workers:add_certificate'), {'title': 'Big', 'file': SimpleUploadedFile('a.pdf', b'0' * (5 * 1024 * 1024 + 1))})
                self.assertContains(big, 'too large')
                c = Certificate.objects.get()
                self.client.post(reverse('workers:delete_certificate', args=[c.pk]))
                self.assertEqual(Certificate.objects.count(), 0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        r = self.client.post(reverse('workers:add_experience'), {'employer_name': 'X', 'role_title': 'Y', 'start_date': '2022-05-01', 'end_date': '2022-01-01'})
        self.assertContains(r, 'cannot be before')
        self.client.post(reverse('workers:add_experience'), {'employer_name': 'X', 'role_title': 'Y', 'start_date': '2022-01-01', 'end_date': '2022-05-01'})
        self.assertEqual(WorkExperience.objects.count(), 1)
        self.client.post(reverse('workers:delete_experience', args=[WorkExperience.objects.get().pk]))
        self.client.post(reverse('workers:delete_skill', args=[Skill.objects.get().pk]))
        self.assertEqual(Skill.objects.count(), 0)

    def test_cannot_delete_other_workers_items(self):
        other = make_worker('Other', username='ot')
        s = Skill.objects.create(worker=other, name='Sewing')
        self.assertEqual(self.client.post(reverse('workers:delete_skill', args=[s.pk])).status_code, 404)

    def test_timeline_public_profile_cv_qr(self):
        a = signed_attestation(self.w, make_employer(), role='Cook')
        WorkExperience.objects.create(worker=self.w, employer_name='Old Cafe', role_title='Helper', start_date=datetime.date(2019, 1, 1))
        Skill.objects.create(worker=self.w, name='Baking')
        t = self.client.get(reverse('workers:timeline'))
        self.assertContains(t, 'Verified')
        self.assertContains(t, 'Self-declared')
        self.client.logout()
        p = self.client.get(reverse('workers:public', args=[self.w.slug]))
        self.assertContains(p, 'Cook')
        self.assertContains(p, 'Baking')
        self.assertEqual(self.client.get(reverse('workers:qr', args=[self.w.slug])).status_code, 200)
        self.assertIn('attachment', self.client.get(reverse('workers:qr', args=[self.w.slug]) + '?download=1')['Content-Disposition'])
        self.assertEqual(self.client.get(reverse('workers:public', args=['nope'])).status_code, 404)
        self.client.login(username='wk', password=PW)
        cv = self.client.get(reverse('workers:cv'))
        self.assertTrue(cv.content.startswith(b'%PDF'))
        self.w.user.is_active = False
        self.w.user.save()
        self.client.logout()
        self.assertEqual(self.client.get(reverse('workers:public', args=[self.w.slug])).status_code, 404)


class AttestationViewTests(TestCase):
    def setUp(self):
        self.w, self.e = make_worker(username='wk'), make_employer(username='em')

    def test_issue_confirm_via_views(self):
        self.client.login(username='em', password=PW)
        r = self.client.post(reverse('attestations:issue'), {'worker_code': f'http://x/w/{self.w.slug}/', 'role_title': 'Driver', 'description': 'Drove', 'start_date': '2023-01-01', 'end_date': ''})
        att = Attestation.objects.get()
        self.assertRedirects(r, reverse('attestations:detail', args=[att.pk]), fetch_redirect_response=False)
        self.assertContains(self.client.get(reverse('attestations:list')), 'Driver')
        self.client.login(username='wk', password=PW)
        self.assertContains(self.client.get(reverse('attestations:detail', args=[att.pk])), 'Confirm and sign')
        self.client.post(reverse('attestations:confirm', args=[att.pk]))
        att.refresh_from_db()
        self.assertEqual(att.status, 'active')
        self.assertEqual(self.client.get(reverse('attestations:list') + '?status=active').status_code, 200)
        self.client.login(username='em', password=PW)
        r = self.client.post(reverse('attestations:rate', args=[att.pk]), {'score': 5, 'punctuality': 4, 'quality': 5, 'honesty': 5, 'comment': 'Great'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.client.get(reverse('attestations:rate', args=[att.pk])).status_code, 200)
        self.client.post(reverse('attestations:revoke', args=[att.pk]), {'reason': 'Wrong person'})
        att.refresh_from_db()
        self.assertEqual(att.status, 'revoked')
        r = self.client.get(reverse('attestations:rate', args=[att.pk]))
        self.assertEqual(r.status_code, 302)

    def test_issue_validation(self):
        self.client.login(username='em', password=PW)
        r = self.client.post(reverse('attestations:issue'), {'worker_code': 'nobody', 'role_title': 'x', 'start_date': '2999-01-01'})
        self.assertContains(r, 'No worker found')
        self.assertContains(r, 'cannot be in the future')
        r = self.client.post(reverse('attestations:issue'), {'worker_code': self.w.slug, 'role_title': 'x', 'start_date': '2023-05-01', 'end_date': '2023-01-01'})
        self.assertContains(r, 'cannot be before')

    def test_unapproved_employer_redirected(self):
        make_employer('Pending Org', approved=False, username='pend')
        self.client.login(username='pend', password=PW)
        self.assertEqual(self.client.get(reverse('attestations:issue')).status_code, 302)
        self.assertContains(self.client.get(reverse('dashboard:home')), 'Pending approval')

    def test_worker_reject_view_and_wrong_user_actions(self):
        att = services.create_attestation(self.e, self.w, 'Cook', '', datetime.date(2023, 1, 1), None)
        other = make_worker('Other', username='ot')
        self.client.login(username='ot', password=PW)
        self.client.post(reverse('attestations:confirm', args=[att.pk]), follow=True)
        att.refresh_from_db()
        self.assertEqual(att.status, 'pending')
        self.client.login(username='wk', password=PW)
        self.client.post(reverse('attestations:reject', args=[att.pk]))
        att.refresh_from_db()
        self.assertEqual(att.status, 'rejected')

    def test_get_not_allowed_for_state_changes(self):
        att = services.create_attestation(self.e, self.w, 'Cook', '', datetime.date(2023, 1, 1), None)
        self.client.login(username='wk', password=PW)
        self.assertEqual(self.client.get(reverse('attestations:confirm', args=[att.pk])).status_code, 405)

    def test_employer_verify_worker_lookup(self):
        self.client.login(username='em', password=PW)
        r = self.client.post(reverse('employers:verify_worker'), {'worker_code': self.w.slug})
        self.assertRedirects(r, reverse('workers:public', args=[self.w.slug]), fetch_redirect_response=False)
        r = self.client.post(reverse('employers:verify_worker'), {'worker_code': f'https://site/w/{self.w.slug}/qr.png'})
        self.assertEqual(r.status_code, 302)
        self.assertContains(self.client.post(reverse('employers:verify_worker'), {'worker_code': 'zzz'}), 'No worker found')
        r = self.client.post(reverse('employers:edit'), {'organisation_name': 'Renamed', 'org_type': 'ngo', 'description': '', 'location': '', 'registration_number': ''})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.client.get(reverse('employers:edit')).status_code, 200)


class DisputeViewTests(TestCase):
    def setUp(self):
        self.w, self.e, self.admin = make_worker(username='wk'), make_employer(username='em'), make_admin()
        self.att = signed_attestation(self.w, self.e)

    def test_dispute_lifecycle_uphold_and_revoke(self):
        self.client.login(username='wk', password=PW)
        r = self.client.post(reverse('disputes:new', args=[self.att.pk]), {'reason': 'Dates are wrong'})
        d = Dispute.objects.get()
        self.assertRedirects(r, reverse('disputes:detail', args=[d.pk]), fetch_redirect_response=False)
        self.att.refresh_from_db()
        self.assertEqual(self.att.status, 'disputed')
        self.assertTrue(Notification.objects.filter(user=self.admin).exists())
        self.assertContains(self.client.get(reverse('disputes:list')), 'Housekeeper')
        self.assertEqual(self.client.post(reverse('disputes:resolve', args=[d.pk]), {'decision': 'uphold', 'note': 'x'}).status_code, 403)
        self.client.login(username='boss', password=PW)
        self.assertContains(self.client.get(reverse('disputes:detail', args=[d.pk])), 'Resolve dispute')
        self.client.post(reverse('disputes:resolve', args=[d.pk]), {'decision': 'uphold', 'note': 'Records match'})
        self.att.refresh_from_db()
        d.refresh_from_db()
        self.assertEqual((self.att.status, d.status), ('active', 'upheld'))
        # second dispute -> revoke
        d2 = dsvc.open_dispute(self.att, self.e.user, 'Employer error')
        self.client.post(reverse('disputes:resolve', args=[d2.pk]), {'decision': 'revoke', 'note': 'Confirmed error'})
        self.att.refresh_from_db()
        self.assertEqual(self.att.status, 'revoked')
        self.client.post(reverse('disputes:resolve', args=[d2.pk]), {'decision': 'revoke', 'note': 'again'})
        self.client.post(reverse('disputes:resolve', args=[d2.pk]), {'decision': '', 'note': ''})

    def test_dispute_permissions(self):
        stranger = make_worker('Str', username='str')
        self.client.login(username='str', password=PW)
        self.assertEqual(self.client.get(reverse('disputes:new', args=[self.att.pk])).status_code, 403)
        d = dsvc.open_dispute(self.att, self.w.user, 'Wrong')
        self.assertEqual(self.client.get(reverse('disputes:detail', args=[d.pk])).status_code, 403)
        with self.assertRaises(Exception):
            dsvc.open_dispute(self.att, self.w.user, 'again')  # already disputed
        self.assertEqual(self.client.get(reverse('disputes:evidence', args=[d.pk])).status_code, 403)

    def test_evidence_download(self):
        tmp = tempfile.mkdtemp()
        try:
            with override_settings(PRIVATE_ROOT=tmp):
                self.client.login(username='wk', password=PW)
                self.client.post(reverse('disputes:new', args=[self.att.pk]), {'reason': 'See proof', 'evidence': SimpleUploadedFile('p.pdf', b'%PDF-1')})
                d = Dispute.objects.get()
                self.assertEqual(self.client.get(reverse('disputes:evidence', args=[d.pk])).status_code, 200)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class AdminFeatureTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.client.login(username='boss', password=PW)

    def test_approve_and_suspend_employer(self):
        e = make_employer('Pending Org', approved=False, username='pe')
        self.assertContains(self.client.get(reverse('dashboard:home')), 'Pending Org')
        self.client.post(reverse('dashboard:employer_action', args=[e.pk, 'approve']))
        e.refresh_from_db()
        self.assertTrue(e.can_issue)
        self.assertTrue(e.key_id.startswith('k-'))
        self.assertEqual(self.client.get(reverse('dashboard:employers')).status_code, 200)
        self.client.post(reverse('dashboard:employer_action', args=[e.pk, 'suspend']))
        e.refresh_from_db()
        self.assertFalse(e.can_issue)
        self.client.post(reverse('dashboard:employer_action', args=[e.pk, 'bogus']))

    def test_user_management(self):
        w = make_worker(username='target')
        self.assertContains(self.client.get(reverse('dashboard:users') + '?q=target&role=worker'), 'target')
        self.client.post(reverse('dashboard:toggle_user', args=[w.user.pk]))
        w.user.refresh_from_db()
        self.assertFalse(w.user.is_active)
        self.client.post(reverse('dashboard:toggle_user', args=[self.admin.pk]))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_flags_verifications_audit(self):
        a = signed_attestation()
        f = FraudFlag.objects.create(attestation=a, rule_code='R2', severity='high', reason='test')
        self.assertContains(self.client.get(reverse('dashboard:flags')), 'test')
        self.client.post(reverse('dashboard:flag_action', args=[f.pk, 'confirmed']))
        f.refresh_from_db()
        self.assertEqual(f.status, 'confirmed')
        self.client.post(reverse('dashboard:flag_action', args=[f.pk, 'nonsense']))
        self.client.get(reverse('verification:result', args=[a.verification_code]))
        self.assertContains(self.client.get(reverse('dashboard:verifications') + '?result=verified'), a.verification_code)
        r = self.client.get(reverse('audit:list') + '?check=1&action=attestation')
        self.assertContains(r, 'Hash chain intact')
        self.assertTrue(verify_chain()[0])

    def test_notifications_flow(self):
        w = make_worker(username='nw')
        services.create_attestation(make_employer(username='ne'), w, 'Cook', '', datetime.date(2023, 1, 1), None)
        self.client.login(username='nw', password=PW)
        self.assertContains(self.client.get(reverse('notifications:list')), 'wants to attest')
        n = Notification.objects.get(user=w.user)
        r = self.client.post(reverse('notifications:read', args=[n.pk]))
        self.assertEqual(r.status_code, 302)
        self.client.post(reverse('notifications:read_all'))
        self.assertEqual(Notification.objects.filter(user=w.user, is_read=False).count(), 0)
        self.assertEqual(self.client.post(reverse('notifications:read', args=[99999])).status_code, 404)
