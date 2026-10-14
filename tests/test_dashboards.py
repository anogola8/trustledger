"""Tests for role-specific dashboards."""
from django.test import TestCase
from django.urls import reverse

from tests.helpers import make_worker, make_employer, make_admin


class WorkerDashboardTests(TestCase):
    def setUp(self):
        self.worker = make_worker('Dash Worker')

    def test_worker_dashboard_loads(self):
        self.client.force_login(self.worker.user)
        response = self.client.get(reverse('dashboard:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dash Worker')
        self.assertContains(response, 'Trust Score')

    def test_worker_dashboard_has_portfolio_button(self):
        self.client.force_login(self.worker.user)
        response = self.client.get(reverse('dashboard:home'))
        self.assertContains(response, 'View Portfolio')


class EmployerDashboardTests(TestCase):
    def setUp(self):
        self.employer = make_employer('Dash Co', approved=True)

    def test_employer_dashboard_loads(self):
        self.client.force_login(self.employer.user)
        response = self.client.get(reverse('dashboard:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dash Co')
        self.assertContains(response, 'Issue Attestation')

    def test_pending_employer_sees_pending_badge(self):
        self.employer.status = 'pending'
        self.employer.save()
        self.client.force_login(self.employer.user)
        response = self.client.get(reverse('dashboard:home'))
        self.assertContains(response, 'Pending approval')


class AdminDashboardTests(TestCase):
    def setUp(self):
        self.admin = make_admin()

    def test_admin_dashboard_loads(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('dashboard:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Operations Center')

    def test_admin_users_page(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('dashboard:users'))
        self.assertEqual(response.status_code, 200)

    def test_admin_employers_page(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('dashboard:employers'))
        self.assertEqual(response.status_code, 200)

    def test_admin_flags_page(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('dashboard:flags'))
        self.assertEqual(response.status_code, 200)

    def test_admin_verifications_page(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('dashboard:verifications'))
        self.assertEqual(response.status_code, 200)

    def test_non_admin_blocked_from_admin_pages(self):
        worker = make_worker('Nobody')
        self.client.force_login(worker.user)
        response = self.client.get(reverse('dashboard:users'))
        self.assertEqual(response.status_code, 403)