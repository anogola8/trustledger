import datetime

from django.contrib.auth import get_user_model

from attestations import services
from employers.models import EmployerProfile
from workers.models import WorkerProfile

User = get_user_model()
PW = 'S3cure-Pass-99'


def make_worker(name='Amina Wanjiru', username=None):
    username = username or name.split()[0].lower() + str(User.objects.count())
    u = User.objects.create_user(username, f'{username}@x.co', PW, role='worker')
    return WorkerProfile.objects.create(user=u, full_name=name)


def make_employer(name='Njeri Household', approved=True, username=None):
    username = username or 'emp' + str(User.objects.count())
    u = User.objects.create_user(username, f'{username}@x.co', PW, role='employer')
    e = EmployerProfile.objects.create(user=u, organisation_name=name)
    if approved:
        e.approve()
    return e


def make_admin(username='boss'):
    return User.objects.create_user(username, 'a@x.co', PW, role='admin')


def signed_attestation(worker=None, employer=None, role='Housekeeper', start=None, end=None, description='Daily cleaning and cooking for a family of five.'):
    worker = worker or make_worker()
    employer = employer or make_employer()
    start = start or datetime.date(2022, 1, 1)
    att = services.create_attestation(employer, worker, role, description, start, end)
    return services.confirm(att, worker.user)
