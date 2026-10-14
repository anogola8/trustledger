from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from core.utils import hash_ip

from .models import VerificationRequest
from .services import verify_and_log


class VerifyAPIView(APIView):
    """Public, unauthenticated, throttled."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'verify'

    def get(self, request, code):
        res = verify_and_log(code, VerificationRequest.Method.API, hash_ip(request))
        body = {'status': res.status, 'valid': res.ok, 'reason': res.reason}
        if res.attestation and res.status in ('verified', 'revoked', 'disputed'):
            a = res.attestation
            body['attestation'] = {'worker': a.worker.full_name, 'role': a.role_title, 'issuer': a.employer.organisation_name,
                                   'start': a.start_date, 'end': a.end_date, 'code': a.verification_code,
                                   'signed_at': a.confirmed_at, 'key_id': a.signature.key_id, 'algorithm': a.signature.algorithm}
        return Response(body, status=404 if res.status == 'not_found' else 200)
