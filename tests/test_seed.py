from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from verification.services import verify_code
from workers.models import WorkerProfile


class SeedDemoTests(TestCase):
    def test_seed_is_idempotent_and_produces_verifiable_records(self):
        out = StringIO()
        call_command('seed_demo', stdout=out)
        call_command('seed_demo', stdout=StringIO())
        w = WorkerProfile.objects.get(user__username='amina')
        self.assertEqual(w.attestations.filter(status='active').count(), 3)
        for a in w.attestations.all():
            self.assertTrue(verify_code(a.verification_code).ok)
        self.assertIn('Demo data ready', out.getvalue())
