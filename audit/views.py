from django.core.paginator import Paginator
from django.shortcuts import render

from core.permissions import role_required

from .models import AuditLog
from .services import verify_chain


@role_required('admin')
def audit_list(request):
    qs = AuditLog.objects.select_related('actor').order_by('-id')
    action = request.GET.get('action', '').strip()
    if action:
        qs = qs.filter(action__icontains=action)
    page = Paginator(qs, 25).get_page(request.GET.get('page'))
    chain = None
    if request.GET.get('check'):
        chain = verify_chain()
    return render(request, 'audit/list.html', {'page': page, 'action': action, 'chain': chain})
