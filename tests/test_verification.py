from django.test import TestCase
from django.urls import reverse

from attestations import services
from attestations.models import Attestation, AttestationSignature
from verification.models import VerificationRequest
from verification.services import verify_code

from .helpers import make_admin, signed_attestation


class VerifyServiceTests(TestCase):
    def setUp(self):
        self.att = signed_attestation()

    def test_valid(self):
        r = verify_code(self.att.verification_code)
        self.assertTrue(r.ok)
        self.assertEqual(verify_code(' ' + self.att.verification_code.lower() + ' ').status, 'verified')

    def test_not_found(self):
        self.assertEqual(verify_code('TL-AAAAA-BBBBB').status, 'not_found')

    def test_tampered_fact_detected(self):
        Attestation.objects.filter(pk=self.att.pk).update(role_title='Manager')
        r = verify_code(self.att.verification_code)
        self.assertEqual(r.status, 'invalid')
        self.assertIn('tampering', r.reason)

    def test_tampered_hash_and_signature_detected(self):
        sig = self.att.signature
        AttestationSignature.objects.filter(pk=sig.pk).update(signature='AAAA' + sig.signature[4:])
        self.assertEqual(verify_code(self.att.verification_code).status, 'invalid')

    def test_forged_with_other_key_detected(self):
        from attestations import crypto
        _, _, enc = crypto.generate_keypair()
        forged = crypto.sign_hash(enc, self.att.payload_hash)
        AttestationSignature.objects.filter(pk=self.att.signature.pk).update(signature=forged)
        self.assertEqual(verify_code(self.att.verification_code).status, 'invalid')

    def test_revoked_and_disputed_and_suspended(self):
        services.revoke(self.att, self.att.employer.user, 'Mistake')
        r = verify_code(self.att.verification_code)
        self.assertEqual((r.status, r.reason), ('revoked', 'Mistake'))
        a2 = signed_attestation()
        Attestation.objects.filter(pk=a2.pk).update(status='disputed')
        self.assertEqual(verify_code(a2.verification_code).status, 'disputed')
        a3 = signed_attestation()
        a3.employer.suspend()
        self.assertEqual(verify_code(a3.verification_code).status, 'invalid')


class VerifyViewTests(TestCase):
    def setUp(self):
        self.att = signed_attestation()
        self.code = self.att.verification_code

    def test_public_result_page_and_logging(self):
        r = self.client.get(reverse('verification:result', args=[self.code]))
        self.assertContains(r, 'VERIFIED')
        self.assertTrue(VerificationRequest.objects.filter(result='verified', attestation=self.att).exists())
        self.assertNotContains(r, '127.0.0.1')

    def test_unknown_code_404(self):
        self.assertEqual(self.client.get(reverse('verification:result', args=['TL-ZZZZZ-ZZZZZ'])).status_code, 404)

    def test_form_redirects(self):
        r = self.client.post(reverse('verification:home'), {'code': ' tl-abcde-fghjk '})
        self.assertRedirects(r, '/verify/TL-ABCDE-FGHJK/', fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse('verification:home')).status_code, 200)

    def test_qr_and_pdf(self):
        r = self.client.get(reverse('verification:qr', args=[self.code]) + '?download=1')
        self.assertEqual(r['Content-Type'], 'image/png')
        self.assertIn('attachment', r['Content-Disposition'])
        self.assertTrue(r.content.startswith(b'\x89PNG'))
        p = self.client.get(reverse('verification:report', args=[self.code]))
        self.assertEqual(p['Content-Type'], 'application/pdf')
        self.assertTrue(p.content.startswith(b'%PDF'))
        self.assertEqual(self.client.get(reverse('verification:report', args=['TL-ZZZZZ-ZZZZZ'])).status_code, 404)

    def test_rate_limit(self):
        from django.core.cache import cache
        cache.clear()
        codes = [reverse('verification:result', args=[self.code])] * 61
        statuses = [self.client.get(u).status_code for u in codes]
        self.assertEqual(statuses[0], 200)
        self.assertEqual(statuses[-1], 429)
        cache.clear()
