import datetime

from django.test import TestCase
from django.utils import timezone

from attestations import services
from attestations.models import Attestation
from employers.models import EmployerRating
from trustscore import services as ts
from trustscore.models import FraudFlag, TrustScore, WorkerBadge
from trustscore.tasks import recompute_trust_score, run_fraud_checks

from .helpers import make_employer, make_worker, signed_attestation


class ScoreTests(TestCase):
    def test_no_attestations_gives_zero(self):
        w = make_worker()
        s = ts.recompute(w)
        self.assertEqual(float(s.value), 0.0)
        self.assertFalse(WorkerBadge.objects.filter(worker=w).exists())

    def test_score_grows_with_verified_work_and_is_explainable(self):
        w = make_worker()
        today = datetime.date.today()
        for i in range(3):
            signed_attestation(w, make_employer(f'Org {i}'), role=f'Job {i}', start=today - datetime.timedelta(days=900 - i * 300), end=today - datetime.timedelta(days=700 - i * 300))
        s = w.trust_scores.first()
        c = s.components
        self.assertEqual(c['active_attestations'], 3)
        self.assertEqual(c['employers'], 3)
        self.assertGreater(float(s.value), 20)
        self.assertLessEqual(float(s.value), 100)
        self.assertEqual(float(ts.score_from_components(c)), float(s.value))
        codes = set(WorkerBadge.objects.filter(worker=w).values_list('code', flat=True))
        self.assertTrue({'FIRST_VERIFIED', 'MULTI_EMPLOYER', 'CLEAN_RECORD'} <= codes)

    def test_ratings_raise_quality_and_top_rated_badge(self):
        w = make_worker()
        today = datetime.date.today()
        atts = [signed_attestation(w, make_employer(f'E{i}'), start=today - datetime.timedelta(days=400), end=today - datetime.timedelta(days=100)) for i in range(3)]
        before = float(w.trust_scores.first().value)
        for a in atts:
            EmployerRating.objects.create(attestation=a, employer=a.employer, worker=w, score=5)
        s = ts.recompute(w)
        self.assertGreater(float(s.value), before)
        self.assertTrue(WorkerBadge.objects.filter(worker=w, code='TOP_RATED').exists())

    def test_revoked_attestation_removes_value_and_badges(self):
        w = make_worker()
        a = signed_attestation(w)
        self.assertGreater(float(w.trust_scores.first().value), 0)
        services.revoke(a, a.employer.user, 'Mistake')
        self.assertEqual(float(w.trust_scores.first().value), 0.0)
        self.assertFalse(WorkerBadge.objects.filter(worker=w).exists())

    def test_overlapping_months_not_double_counted(self):
        w = make_worker()
        d = datetime.date
        a = [Attestation(worker=w, employer=make_employer(f'X{i}'), role_title='r', start_date=s, end_date=e)
             for i, (s, e) in enumerate([(d(2023, 1, 1), d(2023, 12, 31)), (d(2023, 6, 1), d(2024, 6, 30))])]
        months = ts._months_covered(a, d(2025, 1, 1))
        self.assertAlmostEqual(months, 18, delta=0.5)

    def test_high_flag_penalty_capped(self):
        w = make_worker()
        a = signed_attestation(w)
        for i in range(5):
            FraudFlag.objects.create(attestation=a, rule_code=f'R{i}', severity='high', reason='x')
        c = ts.compute_components(w)
        self.assertEqual(c['F'], 30)
        self.assertAlmostEqual(float(ts.score_from_components(c)), float(w.trust_scores.first().value) - 30, delta=0.01 + 14.44)
        self.assertLess(float(ts.score_from_components(c)), float(w.trust_scores.first().value))

    def test_tasks(self):
        w = make_worker()
        a = signed_attestation(w)
        self.assertIsNotNone(recompute_trust_score(w.pk))
        self.assertIsNone(recompute_trust_score(999999))
        self.assertEqual(run_fraud_checks(str(a.id)), 0)
        self.assertEqual(run_fraud_checks('00000000-0000-0000-0000-000000000000'), 0)


class FraudRuleTests(TestCase):
    def test_r1_burst(self):
        e = make_employer()
        for i in range(12):
            services.create_attestation(e, make_worker(f'W {i}', username=f'w{i}'), f'Role {i}', f'unique {i}', datetime.date(2023, 1, 1), None)
        self.assertTrue(FraudFlag.objects.filter(rule_code='R1').exists())

    def test_r2_new_employer_surge(self):
        e = make_employer()
        for i in range(7):
            services.create_attestation(e, make_worker(f'W {i}', username=f'v{i}'), f'Role {i}', f'unique {i}', datetime.date(2023, 1, 1), None)
        self.assertTrue(FraudFlag.objects.filter(rule_code='R2', severity='high').exists())

    def test_r3_overlap(self):
        w = make_worker()
        signed_attestation(w, make_employer('A'), start=datetime.date(2022, 1, 1), end=datetime.date(2023, 12, 31))
        services.create_attestation(make_employer('B'), w, 'Second job', 'x', datetime.date(2022, 6, 1), datetime.date(2023, 6, 1))
        self.assertTrue(FraudFlag.objects.filter(rule_code='R3').exists())

    def test_r4_duplicate_description(self):
        e = make_employer()
        text = 'Excellent worker who did everything perfectly.'
        for i in range(3):
            services.create_attestation(e, make_worker(f'D {i}', username=f'd{i}'), 'Role', text, datetime.date(2023, 1, 1), None)
        self.assertTrue(FraudFlag.objects.filter(rule_code='R4').exists())

    def test_r5_uniform_ratings_and_dedup(self):
        e = make_employer()
        for i in range(5):
            a = signed_attestation(make_worker(f'R {i}', username=f'r{i}'), e, description=f'Unique description number {i} is here')
            EmployerRating.objects.create(attestation=a, employer=e, worker=a.worker, score=5)
        flags = ts.evaluate_attestation(a)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].rule_code, 'R5')
        self.assertEqual(ts.evaluate_attestation(a), [])  # no duplicate open flag
