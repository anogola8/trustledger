from django.contrib import messages
from django.shortcuts import redirect, render

from audit.services import log
from core.permissions import role_required
from workers.models import WorkerProfile

from .forms import EmployerProfileForm, VerifyWorkerForm


@role_required('employer')
def edit_profile(request):
    emp = request.user.employer_profile
    form = EmployerProfileForm(request.POST or None, instance=emp)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log(request.user, 'employer.profile_update', 'employer', emp.pk)
        messages.success(request, 'Employer profile updated.')
        return redirect('dashboard:home')
    return render(request, 'form.html', {'form': form, 'title': 'Employer profile', 'back': 'dashboard:home'})


@role_required('employer')
def verify_worker(request):
    """Look up a worker by profile code/link and open their public, signed record."""
    form = VerifyWorkerForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        code = form.cleaned_data['worker_code'].strip().rstrip('/').split('/')[-1]
        if code.lower() == 'qr.png':
            code = form.cleaned_data['worker_code'].strip().rstrip('/').split('/')[-2]
        if WorkerProfile.objects.filter(slug=code).exists():
            return redirect('workers:public', slug=code)
        form.add_error('worker_code', 'No worker found with that code.')
    return render(request, 'form.html', {'form': form, 'title': 'Verify a worker', 'back': 'dashboard:home', 'submit': 'Look up'})
