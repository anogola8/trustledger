import datetime

from django.test import TestCase

from attestations import crypto, services
from attestations.models import Attestation
from attestations.services import ServiceError
from audit.services import verify_chain
from notifications.models import Notification

from .helpers import make_admin, make_employer, make_worker, signed_attestation


class CryptoTests(TestCase):
    def test_sign_and_verify_roundtrip(self):
        key_id, pub, enc = crypto.generate_keypair()
        h = crypto.hash_payload({'a': 1, 'b': [1, 2]})
        sig = crypto.sign_hash(enc, h)
        self.assertTrue(crypto.verify_signature(pub, sig, h))
        self.assertFalse(crypto.verify_signature(pub, sig, crypto.hash_payload({'a': 2})))
        self.assertFalse(crypto.verify_signature(pub, 'not-base64!!', h))

    def test_canonical_json_is_order_independent(self):
        self.assertEqual(crypto.hash_payload({'a': 1, 'b': 2}), crypto.hash_payload({'b': 2, 'a': 1}))

    def test_private_key_is_encrypted_at_rest(self):
        _, pub, enc = crypto.generate_keypair()
        self.assertNotIn(pub, enc)
        self.assertTrue(enc.startswith('gAAAA'))  # Fernet token


class WorkflowTests(TestCase):
    def test_full_issue_confirm_sign_flow(self):
        w, e = make_worker(), make_employer()
        att = services.create_attestation(e, w, 'Cook', 'Cooking', datetime.date(2023, 1, 1), None)
        self.assertEqual(att.status, Attestation.Status.PENDING)
        self.assertTrue(Notification.objects.filter(user=w.user).exists())
        att = services.confirm(att, w.user)
        self.assertEqual(att.status, Attestation.Status.ACTIVE)
        self.assertRegex(att.verification_code, r'^TL-[A-Z2-9]{5}-[A-Z2-9]{5}$')
        self.assertEqual(len(att.payload_hash), 64)
        self.assertEqual(att.signature.algorithm, 'Ed25519')
        self.assertTrue(w.trust_scores.exists())

    def test_unapproved_employer_cannot_issue(self):
        e = make_employer(approved=False)
        with self.assertRaises(ServiceError):
            services.create_attestation(e, make_worker(), 'Cook', '', datetime.date(2023, 1, 1), None)

    def test_only_named_worker_can_confirm_or_reject(self):
        w, other, e = make_worker(), make_worker('Other Person'), make_employer()
        att = services.create_attestation(e, w, 'Cook', '', datetime.date(2023, 1, 1), None)
        with self.assertRaises(ServiceError):
            services.confirm(att, other.user)
        with self.assertRaises(ServiceError):
            services.reject(att, other.user)

    def test_cannot_confirm_twice_or_after_suspension(self):
        att = signed_attestation()
        with self.assertRaises(ServiceError):
            services.confirm(att, att.worker.user)
        w, e = make_worker('B Worker'), make_employer('Org B')
        pending = services.create_attestation(e, w, 'Cook', '', datetime.date(2023, 1, 1), None)
        e.suspend()
        with self.assertRaises(ServiceError):
            services.confirm(pending, w.user)

    def test_reject(self):
        w, e = make_worker(), make_employer()
        att = services.create_attestation(e, w, 'Cook', '', datetime.date(2023, 1, 1), None)
        services.reject(att, w.user)
        att.refresh_from_db()
        self.assertEqual(att.status, 'rejected')
        with self.assertRaises(ServiceError):
            services.reject(att, w.user)

    def test_revoke_rules(self):
        att = signed_attestation()
        stranger = make_employer('Stranger Co')
        with self.assertRaises(ServiceError):
            services.revoke(att, stranger.user, 'x')
        with self.assertRaises(ServiceError):
            services.revoke(att, att.employer.user, '   ')
        services.revoke(att, att.employer.user, 'Issued by mistake')
        att.refresh_from_db()
        self.assertEqual(att.status, 'revoked')
        with self.assertRaises(ServiceError):
            services.revoke(att, att.employer.user, 'again')

    def test_admin_can_revoke(self):
        att = signed_attestation()
        services.revoke(att, make_admin(), 'Fraud confirmed')
        att.refresh_from_db()
        self.assertEqual(att.status, 'revoked')

    def test_audit_chain_stays_intact_and_detects_tampering(self):
        signed_attestation()
        self.assertEqual(verify_chain(), (True, None))
        from audit.models import AuditLog
        first = AuditLog.objects.order_by('id').first()
        AuditLog.objects.filter(pk=first.pk).update(action='tampered')
        ok, bad = verify_chain()
        self.assertFalse(ok)
        self.assertEqual(bad, first.pk)
