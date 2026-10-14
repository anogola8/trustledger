"""Creates demo accounts and signed attestations for demonstrations and the project defense."""
import datetime
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from attestations import services
from employers.models import EmployerProfile
from workers.models import Skill, WorkerProfile


class Command(BaseCommand):
    help = 'Seed demo data (admin, employers, workers, signed attestations).'

    def handle(self, *args, **opts):
        User = get_user_model()
        pw = os.environ.get('DEMO_PASSWORD', 'DemoPass#2026')
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', pw)
        w_user, _ = User.objects.get_or_create(username='amina', defaults={'email': 'amina@example.com', 'role': 'worker'})
        w_user.set_password(pw); w_user.save()
        worker, _ = WorkerProfile.objects.get_or_create(user=w_user, defaults={'full_name': 'Amina Wanjiru', 'headline': 'Experienced domestic worker and cook', 'location': 'Meru'})
        for name, lvl in [('Cooking', 3), ('Childcare', 2), ('Housekeeping', 3)]:
            Skill.objects.get_or_create(worker=worker, name=name, defaults={'level': lvl, 'years': 5})
        orgs = []
        for uname, org in [('njeri', 'Njeri Household'), ('sunrise', 'Sunrise Care Ltd'), ('mamarosa', 'Mama Rosa Cafe')]:
            u, _ = User.objects.get_or_create(username=uname, defaults={'email': f'{uname}@example.com', 'role': 'employer'})
            u.set_password(pw); u.save()
            e, _ = EmployerProfile.objects.get_or_create(user=u, defaults={'organisation_name': org})
            if not e.can_issue:
                e.approve()
            orgs.append(e)
        if not worker.attestations.exists():
            today = datetime.date.today()
            jobs = [('Housekeeper', today.replace(year=today.year - 3), today.replace(year=today.year - 1)),
                    ('Caregiver', today.replace(year=today.year - 1), None), ('Cook', today.replace(year=today.year - 5), today.replace(year=today.year - 3))]
            for org, (role, s, e) in zip(orgs, jobs):
                att = services.create_attestation(org, worker, role, f'{role} duties performed reliably.', s, e)
                services.confirm(att, worker.user)
        self.stdout.write(self.style.SUCCESS('Demo data ready.'))
        self.stdout.write(f'Logins (password from DEMO_PASSWORD or default): admin, amina (worker), njeri/sunrise/mamarosa (employers)')
        self.stdout.write(f'Worker profile code: {worker.slug}')
        for a in worker.attestations.filter(status="active"):
            self.stdout.write(f'  verify: /verify/{a.verification_code}/  ({a.role_title})')
