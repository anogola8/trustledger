from django.http import HttpResponse
from django.shortcuts import redirect, render

from core.pdf import Paragraph, Spacer, build_pdf, qr_flowable, qr_png_bytes, table
from core.ratelimit import allow
from core.utils import absolute_url, hash_ip, normalise_code

from .forms import CodeForm
from .models import VerificationRequest
from .services import verify_and_log, verify_code


def home(request):
    form = CodeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        return redirect('verification:result', code=normalise_code(form.cleaned_data['code']))
    return render(request, 'verification/home.html', {'form': form})


def result(request, code):
    if not allow(f'verify:{hash_ip(request)}', limit=60, window=60):
        return render(request, 'verification/throttled.html', status=429)
    method = VerificationRequest.Method.CODE if request.GET.get('src') == 'code' else VerificationRequest.Method.LINK
    res = verify_and_log(code, method, hash_ip(request))
    status = 404 if res.status == 'not_found' else 200
    return render(request, 'verification/result.html', {'res': res, 'code': normalise_code(code),
                                                         'url': absolute_url(request.path)}, status=status)


def qr(request, code):
    code = normalise_code(code)
    resp = HttpResponse(qr_png_bytes(absolute_url(f'/verify/{code}/')), content_type='image/png')
    if request.GET.get('download'):
        resp['Content-Disposition'] = f'attachment; filename="{code}.png"'
    return resp


def report_pdf(request, code):
    """Downloadable verification report, generated from a live verification run."""
    if not allow(f'verify:{hash_ip(request)}', limit=60, window=60):
        return HttpResponse('Too many requests', status=429)
    res = verify_and_log(code, VerificationRequest.Method.LINK, hash_ip(request))
    if res.status == 'not_found':
        return HttpResponse('Not found', status=404)
    att, url = res.attestation, absolute_url(f'/verify/{normalise_code(code)}/')

    def story(st):
        s = [Paragraph('TrustLedger Verification Report', st['title']),
             Paragraph(f'Result: <b>{res.status.upper()}</b>' + (f' &mdash; {res.reason}' if res.reason else ''), st['body']), Spacer(1, 8)]
        rows = [['Field', 'Value'], ['Worker', att.worker.full_name], ['Role', att.role_title], ['Issuer', att.employer.organisation_name],
                ['Period', f"{att.start_date:%d %b %Y} - " + (f"{att.end_date:%d %b %Y}" if att.end_date else 'present')],
                ['Verification code', att.verification_code or ''], ['Signed at', f'{att.confirmed_at:%d %b %Y %H:%M} UTC' if att.confirmed_at else ''],
                ['Algorithm', 'Ed25519 over SHA-256 payload hash'], ['Key ID', getattr(att.signature, 'key_id', '') if hasattr(att, 'signature') else ''],
                ['Payload hash', att.payload_hash[:32] + '...' if att.payload_hash else '']]
        s += [table(rows, [45 * 2.83, 110 * 2.83]), Spacer(1, 10), qr_flowable(url),
              Paragraph(f'Re-verify at {url}', st['small']),
              Paragraph('A digital signature proves who issued the statement and that it has not been altered. It does not by itself prove the statement is true.', st['small'])]
        return s

    resp = HttpResponse(build_pdf(story), content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="verification-{normalise_code(code)}.pdf"'
    return resp
