"""Tests for the worker portfolio (private + public)."""
from datetime import date

from django.test import TestCase
from django.urls import reverse

from attestations.models import Attestation
from workers.models import Certificate, Skill
from tests.helpers import make_worker, make_employer, PW


class PortfolioAccessTests(TestCase):
    def setUp(self):
        self.worker = make_worker('Test Worker')
        self.other_worker = make_worker('Other Worker')
        self.employer = make_employer('Test Org')

    def test_portfolio_requires_login(self):
        response = self.client.get(reverse('workers:portfolio'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_portfolio_blocked_for_employer(self):
        self.client.force_login(self.employer.user)
        response = self.client.get(reverse('workers:portfolio'))
        self.assertEqual(response.status_code, 403)

    def test_portfolio_allowed_for_worker(self):
        self.client.force_login(self.worker.user)
        response = self.client.get(reverse('workers:portfolio'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Worker')

    def test_public_portfolio_accessible_without_login(self):
        response = self.client.get(reverse('workers:portfolio_public', args=[self.worker.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Worker')

    def test_public_portfolio_unknown_slug_404(self):
        response = self.client.get(reverse('workers:portfolio_public', args=['does-not-exist']))
        self.assertEqual(response.status_code, 404)


class PortfolioContentTests(TestCase):
    def setUp(self):
        self.worker = make_worker('Jane Doe')
        self.employer = make_employer('Sunrise Ltd')

    def test_verified_work_shows_in_portfolio(self):
        Attestation.objects.create(
            worker=self.worker, employer=self.employer,
            role_title='Cleaner', description='Great work',
            start_date=date(2023, 1, 1), end_date=date(2024, 1, 1),
            status='active', verification_code='TL-ABCD-EFGH',
        )
        self.client.force_login(self.worker.user)
        response = self.client.get(reverse('workers:portfolio'))
        self.assertContains(response, 'Cleaner')
        self.assertContains(response, 'Sunrise Ltd')

    def test_pending_attestation_shown_only_to_owner(self):
        Attestation.objects.create(
            worker=self.worker, employer=self.employer,
            role_title='Pending Role', start_date=date(2024, 1, 1),
            status='pending',
        )
        self.client.force_login(self.worker.user)
        response = self.client.get(reverse('workers:portfolio'))
        self.assertContains(response, 'Pending Role')

        self.client.logout()
        response = self.client.get(reverse('workers:portfolio_public', args=[self.worker.slug]))
        self.assertNotContains(response, 'Pending Role')

    def test_skills_shown_in_portfolio(self):
        Skill.objects.create(worker=self.worker, name='Cleaning', level=3, years=2)
        self.client.force_login(self.worker.user)
        response = self.client.get(reverse('workers:portfolio'))
        self.assertContains(response, 'Cleaning')

    def test_certificate_shown_in_portfolio(self):
        Certificate.objects.create(
            worker=self.worker, title='First Aid', issuing_body='Red Cross', year=2023,
        )
        self.client.force_login(self.worker.user)
        response = self.client.get(reverse('workers:portfolio'))
        self.assertContains(response, 'First Aid')
        self.assertContains(response, 'Red Cross')

    def test_portfolio_shows_portfolio_url(self):
        self.client.force_login(self.worker.user)
        response = self.client.get(reverse('workers:portfolio'))
        self.assertContains(response, self.worker.slug)