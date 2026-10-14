"""Seed the database with realistic Kenyan demo data.

Usage:
    python manage.py seed_big_demo                    # defaults to 500 workers
    python manage.py seed_big_demo --workers 200      # smaller set
    python manage.py seed_big_demo --clear            # wipe first

Idempotent: re-running extends rather than duplicates where possible.
Password for all seeded accounts: Demo1234!
"""
import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import EmailVerification
from attestations import services as att_services
from employers.models import EmployerProfile
from trustscore.models import TrustScore, WorkerBadge
from workers.models import Certificate, Skill, WorkerProfile, WorkExperience

User = get_user_model()
PASSWORD = 'Demo1234!'

# ---------------------------------------------------------------
# Realistic Kenyan data pools
# ---------------------------------------------------------------
FIRST_NAMES = [
    'Amina', 'Grace', 'Faith', 'Mercy', 'Cynthia', 'Esther', 'Naomi', 'Purity', 'Njeri', 'Wanjiku',
    'Otieno', 'Achieng', 'Atieno', 'Nyambura', 'Wairimu', 'Chebet', 'Jepkosgei', 'Naserian',
    'Halima', 'Fatuma', 'Zainab', 'Aisha', 'Maryam', 'Rehema', 'Imani', 'Baraka', 'Neema', 'Tumaini',
    'Brenda', 'Sharon', 'Winnie', 'Millicent', 'Everline', 'Khadija', 'Lucy', 'Beatrice', 'Alice',
    'Dennis', 'Brian', 'Kevin', 'Victor', 'Felix', 'Erick', 'Peter', 'John', 'James', 'Paul',
    'Moses', 'Samuel', 'Isaac', 'Daniel', 'Isaack', 'Abdul', 'Hassan', 'Mohamed', 'Yusuf', 'Ibrahim',
    'Wekesa', 'Wafula', 'Simiyu', 'Kipchoge', 'Kiprotich', 'Kipruto', 'Mutua', 'Kimani', 'Mwangi',
]

LAST_NAMES = [
    'Wanjiru', 'Otieno', 'Mwikali', 'Njoroge', 'Kariuki', 'Ochieng', 'Odhiambo', 'Muthoni',
    'Wambui', 'Kamau', 'Mwangi', 'Kipchoge', 'Cheruiyot', 'Koech', 'Chepkwony', 'Rotich',
    'Yusuf', 'Hassan', 'Abdi', 'Warsame', 'Mohamed', 'Omar', 'Ali', 'Ibrahim',
    'Mutiso', 'Kioko', 'Musyoka', 'Kilonzo', 'Mumo', 'Makau', 'Mwende', 'Nzioka',
    'Wafula', 'Wanyonyi', 'Barasa', 'Simiyu', 'Makokha', 'Khaemba', 'Juma',
    'Shah', 'Patel', 'Singh', 'Odera', 'Onyango', 'Amollo', 'Owino', 'Auko',
]

HEADLINES = [
    'Experienced House Help', 'Reliable Cook', 'Expert Cleaner', 'Child Care Specialist',
    'Laundry & Ironing Pro', 'Experienced Nanny', 'Boda Boda Rider', 'Delivery Rider',
    'Certified Electrician', 'Professional Plumber', 'Fundi wa Mbao', 'Mason & Bricklayer',
    'Painter & Decorator', 'Welder & Fabricator', 'Tailor & Fashion Designer',
    'Hair Stylist', 'Barber', 'Makeup Artist', 'Security Guard', 'Gardener',
    'Tutor (Primary/Secondary)', 'Sales Assistant', 'Shop Attendant', 'Waiter / Waitress',
    'Chef / Cook', 'Driver (Class BCE)', 'Mkokoteni Operator', 'Shoe Shiner',
]

LOCATIONS = [
    ('Kayole', 'Nairobi'), ('Kasarani', 'Nairobi'), ('Kilimani', 'Nairobi'),
    ('Eastleigh', 'Nairobi'), ('Embakasi', 'Nairobi'), ('Roysambu', 'Nairobi'),
    ('Westlands', 'Nairobi'), ('Langata', 'Nairobi'), ('Karen', 'Nairobi'),
    ('Kibera', 'Nairobi'), ('Mathare', 'Nairobi'), ('Dandora', 'Nairobi'),
    ('Nakuru Town', 'Nakuru'), ('Naivasha', 'Nakuru'), ('Gilgil', 'Nakuru'),
    ('Mombasa CBD', 'Mombasa'), ('Nyali', 'Mombasa'), ('Likoni', 'Mombasa'),
    ('Kisumu CBD', 'Kisumu'), ('Milimani', 'Kisumu'), ('Eldoret Town', 'Uasin Gishu'),
    ('Thika Town', 'Kiambu'), ('Nyeri Town', 'Nyeri'), ('Machakos Town', 'Machakos'),
    ('Meru Town', 'Meru'), ('Embu Town', 'Embu'), ('Kericho Town', 'Kericho'),
]

SKILLS = [
    # Domestic
    ('House Cleaning', 'Domestic'), ('Laundry', 'Domestic'), ('Ironing', 'Domestic'),
    ('Cooking (Kenyan)', 'Domestic'), ('Baking', 'Domestic'), ('Child Care', 'Domestic'),
    ('Elderly Care', 'Domestic'), ('Pet Care', 'Domestic'),
    # Trades
    ('Electrical Wiring', 'Trades'), ('Plumbing', 'Trades'), ('Carpentry', 'Trades'),
    ('Masonry', 'Trades'), ('Welding', 'Trades'), ('Painting', 'Trades'), ('Roofing', 'Trades'),
    ('Tiling', 'Trades'), ('Furniture Making', 'Trades'), ('Auto Mechanics', 'Trades'),
    # Transport
    ('Boda Boda Riding', 'Transport'), ('Taxi Driving', 'Transport'),
    ('Truck Driving', 'Transport'), ('Delivery', 'Transport'), ('Mkokoteni', 'Transport'),
    # Personal Services
    ('Hairdressing', 'Personal Care'), ('Barbering', 'Personal Care'), ('Makeup Artistry', 'Personal Care'),
    ('Nail Care', 'Personal Care'), ('Massage', 'Personal Care'), ('Tailoring', 'Personal Care'),
    # Business / Sales
    ('Shop Keeping', 'Business'), ('Sales', 'Business'), ('Cash Handling', 'Business'),
    ('Stock Management', 'Business'), ('Customer Service', 'Business'),
    # Food Service
    ('Waitering', 'Hospitality'), ('Bartending', 'Hospitality'), ('Food Prep', 'Hospitality'),
    ('Catering', 'Hospitality'),
    # Education
    ('Primary Tutoring', 'Education'), ('Secondary Tutoring', 'Education'),
    ('Kiswahili Teaching', 'Education'), ('English Teaching', 'Education'),
    ('Computer Literacy', 'Education'),
    # Security & Other
    ('Security Guarding', 'Security'), ('CCTV Monitoring', 'Security'),
    ('Gardening', 'Outdoor'), ('Landscaping', 'Outdoor'), ('Farming', 'Outdoor'),
]

EMPLOYER_TYPES = [
    'Household', 'Cafe', 'Restaurant', 'Supermarket', 'Salon', 'Barbershop',
    'Hardware', 'Garage', 'Pharmacy', 'Boutique', 'Hotel', 'Lodge', 'School',
    'Church', 'NGO', 'Construction Co.', 'Transport Co.', 'Farm',
]

EMPLOYER_PREFIXES = [
    'Sunrise', 'Mama Rosa', 'Njeri', 'Amani', 'Baraka', 'Tumaini', 'Neema',
    'Kilimani', 'Westlands', 'Nakuru', 'Coastal', 'Highland', 'Rift Valley',
    'Nairobi', 'Mombasa', 'Kisumu', 'Serengeti', 'Mount Kenya', 'Tsavo',
    'Malaika', 'Furaha', 'Imani', 'Upendo', 'Nuru', 'Jua Kali',
]

ATTESTATION_DESCRIPTIONS = [
    'Reliable, punctual and honest. Would hire again.',
    'Excellent work ethic. Went above and beyond.',
    'Trustworthy and skilled. Highly recommended.',
    'Polite, hardworking and always on time.',
    'Consistently delivered quality work.',
    'Great with children. Very patient and caring.',
    'Skilled professional. Clean workmanship.',
    'Always willing to learn. Fast learner.',
    'Handled our family needs with care and respect.',
    'Needed minimal supervision. Very proactive.',
    'Excellent customer service. Kept clients happy.',
    'Trustworthy with money and property.',
    'Handled pressure well. Calm under stress.',
    'Strong technical skills. Fixed complex issues.',
    'Friendly and professional. Great with everyone.',
]

BADGE_CODES = ['first_verified_job', 'experienced', 'trusted', 'highly_rated', 'veteran']


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
def rand_name():
    return f'{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}'


def rand_username(name, used):
    base = name.lower().replace(' ', '.')
    candidate = base
    i = 1
    while candidate in used:
        candidate = f'{base}{i}'
        i += 1
    used.add(candidate)
    return candidate


def rand_date(start_year=2020, end_year=2025):
    return date(
        random.randint(start_year, end_year),
        random.randint(1, 12),
        random.randint(1, 28),
    )

def _mark_verified(user):
    """Create an EmailVerification record marked as verified."""
    from django.utils import timezone
    EmailVerification.objects.get_or_create(
        user=user,
        defaults={'verified_at': timezone.now()},
    )




class Command(BaseCommand):
    help = 'Seed realistic Kenyan demo data.'

    def add_arguments(self, parser):
        parser.add_argument('--workers', type=int, default=500)
        parser.add_argument('--employers', type=int, default=60)
        parser.add_argument('--clear', action='store_true')

    @transaction.atomic
    def handle(self, *args, **opts):
        n_workers = opts['workers']
        n_employers = opts['employers']

        if opts['clear']:
            self.stdout.write(self.style.WARNING('Clearing demo data...'))
            WorkerProfile.objects.all().delete()
            EmployerProfile.objects.all().delete()
            User.objects.exclude(is_superuser=True).delete()

        # ---------------------------------------------------------
        # 1) Employers
        # ---------------------------------------------------------
        self.stdout.write('Creating employers...')
        employers = []
        existing_emp_emails = set(User.objects.values_list('email', flat=True))

        for i in range(n_employers):
            type_ = random.choice(EMPLOYER_TYPES)
            prefix = random.choice(EMPLOYER_PREFIXES)
            org_name = f'{prefix} {type_}'

            email = f'employer{i+1:03d}@trustledger.demo'
            if email in existing_emp_emails:
                continue

            user = User.objects.create_user(
                username=f'employer{i+1:03d}',
                email=email,
                password=PASSWORD,
                role='employer',
            )
            emp = EmployerProfile.objects.create(
                user=user,
                organisation_name=org_name,
            )
            _mark_verified(user)
            # 85% approved, 15% pending (realistic mix)
            if random.random() < 0.85:
                emp.approve()
            else:
                emp.status = 'pending'
                emp.save()
            employers.append(emp)

        self.stdout.write(f'  → {len(employers)} employers')

        # ---------------------------------------------------------
        # 2) Workers
        # ---------------------------------------------------------
        self.stdout.write(f'Creating {n_workers} workers...')
        used_usernames = set(User.objects.values_list('username', flat=True))
        worker_objs = []

        for i in range(n_workers):
            name = rand_name()
            username = rand_username(name, used_usernames)
            email = f'{username}@trustledger.demo'

            user = User.objects.create_user(
                username=username,
                email=email,
                password=PASSWORD,
                role='worker',
            )
            _mark_verified(user)
            loc, county = random.choice(LOCATIONS)
            profile = WorkerProfile.objects.create(
                user=user,
                full_name=name,
                headline=random.choice(HEADLINES),
                bio=(
                    f'{name.split()[0]} has several years of experience. '
                    f'Hardworking, honest, and eager to work.'
                ),
                location=f'{loc}',
                show_skills=True,
                show_certificates=True,
            )
            worker_objs.append(profile)

            if (i + 1) % 50 == 0:
                self.stdout.write(f'  → {i + 1}/{n_workers} workers')

        self.stdout.write(f'  → {len(worker_objs)} workers total')

        # ---------------------------------------------------------
        # 3) Skills
        # ---------------------------------------------------------
        self.stdout.write('Adding skills...')
        skill_objs = []
        for w in worker_objs:
            n_skills = random.randint(1, 5)
            chosen = random.sample(SKILLS, k=n_skills)
            for name_, _cat in chosen:
                try:
                    s = Skill.objects.create(
                        worker=w,
                        name=name_,
                        level=random.choice([1, 2, 2, 3]),
                        years=random.randint(0, 10),
                    )
                    skill_objs.append(s)
                except Exception:
                    pass  # unique constraint
        self.stdout.write(f'  → {len(skill_objs)} skills')

        # ---------------------------------------------------------
        # 4) WorkExperience (self-declared)
        # ---------------------------------------------------------
        self.stdout.write('Adding self-declared experience...')
        exp_count = 0
        for w in worker_objs:
            if random.random() < 0.7:
                n = random.randint(1, 3)
                for _ in range(n):
                    start = rand_date(2016, 2023)
                    end = start + timedelta(days=random.randint(60, 1500))
                    if end > date.today():
                        end = None
                    try:
                        WorkExperience.objects.create(
                            worker=w,
                            employer_name=random.choice(EMPLOYER_PREFIXES) + ' ' + random.choice(EMPLOYER_TYPES),
                            role_title=random.choice(HEADLINES).split('(')[0].strip(),
                            start_date=start,
                            end_date=end,
                            description='Self-declared work experience.',
                        )
                        exp_count += 1
                    except Exception:
                        pass
        self.stdout.write(f'  → {exp_count} experiences')

        # ---------------------------------------------------------
        # 5) Certificates
        # ---------------------------------------------------------
        self.stdout.write('Adding certificates...')
        cert_count = 0
        cert_titles = [
            ('First Aid', 'Kenya Red Cross'),
            ('Food Handling', 'Public Health Dept'),
            ('Electrical Safety', 'EPRA'),
            ('Childcare Level 1', 'NITA'),
            ('Customer Service', 'KIHBT'),
            ('Driving License', 'NTSA'),
            ('Security Training', 'KK Security Academy'),
        ]
        for w in worker_objs:
            if random.random() < 0.5:
                title, issuer = random.choice(cert_titles)
                try:
                    Certificate.objects.create(
                        worker=w,
                        title=title,
                        issuing_body=issuer,
                        year=random.randint(2018, 2025),
                    )
                    cert_count += 1
                except Exception:
                    pass
        self.stdout.write(f'  → {cert_count} certificates')

        # ---------------------------------------------------------
        # 6) Attestations (mixed statuses)
        # ---------------------------------------------------------
        self.stdout.write('Creating attestations...')
        att_count = {'active': 0, 'pending': 0, 'revoked': 0, 'rejected': 0}
        approved_employers = [e for e in employers if e.status == 'approved']

        for w in worker_objs:
            n_atts = random.choices([0, 1, 2, 3, 4], weights=[10, 30, 30, 20, 10])[0]
            for _ in range(n_atts):
                if not approved_employers:
                    break
                emp = random.choice(approved_employers)
                start = rand_date(2018, 2024)
                end = start + timedelta(days=random.randint(90, 1000))
                if end > date.today():
                    end = None

                try:
                    att = att_services.create_attestation(
                        employer=emp,
                        worker=w,
                        role_title=random.choice(HEADLINES).split('(')[0].strip(),
                        description=random.choice(ATTESTATION_DESCRIPTIONS),
                        start_date=start,
                        end_date=end,
                    )
                except Exception:
                    continue

                # 70% confirmed/active, 20% pending, 5% rejected, 5% revoked
                roll = random.random()
                try:
                    if roll < 0.70:
                        att_services.confirm(att, w.user)
                        att_count['active'] += 1
                    elif roll < 0.90:
                        att_count['pending'] += 1
                    elif roll < 0.95:
                        att_services.reject(att, w.user)
                        att_count['rejected'] += 1
                    else:
                        att_services.confirm(att, w.user)
                        att_services.revoke(att, emp.user, 'Issued by mistake')
                        att_count['revoked'] += 1
                except Exception:
                    pass

        self.stdout.write(f'  → Attestations: {att_count}')

        # ---------------------------------------------------------
        # 7) Trust scores + badges
        # ---------------------------------------------------------
        self.stdout.write('Computing trust scores + badges...')
        ts_count = 0
        badge_count = 0
        from trustscore.services import BADGES

        for w in worker_objs:
            active = w.attestations.filter(status='active').count()
            pending = w.attestations.filter(status='pending').count()
            skills_n = w.skills.count()
            certs_n = w.certificates.count()

            # Simple deterministic score
            score = min(
                100,
                20 + active * 12 + skills_n * 3 + certs_n * 5 - pending * 2
            )
            score = max(5, score)

            TrustScore.objects.create(
                worker=w,
                value=Decimal(score),
                components={
                    'active_attestations': active,
                    'skills': skills_n,
                    'certificates': certs_n,
                    'pending': pending,
                },
            )
            ts_count += 1

            # Award badges based on real codes
            codes = []
            if active >= 1:
                codes.append('FIRST_VERIFIED')
            if active >= 3:
                codes.append('MULTI_EMPLOYER')
            if active >= 5:
                codes.append('CLEAN_RECORD')
            if active >= 1 and random.random() < 0.35:
                codes.append('VETERAN')
            if score >= 75:
                codes.append('TOP_RATED')

            for code in codes:
                if code in BADGES:
                    try:
                        WorkerBadge.objects.get_or_create(worker=w, code=code)
                        badge_count += 1
                    except Exception:
                        pass

        self.stdout.write(f'  → {ts_count} trust scores, {badge_count} badges')

        # ---------------------------------------------------------
        # Summary
        # ---------------------------------------------------------
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(f'SEED COMPLETE — password: {PASSWORD}'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'Workers:          {len(worker_objs)}')
        self.stdout.write(f'Employers:        {len(employers)}')
        self.stdout.write(f'Skills:           {len(skill_objs)}')
        self.stdout.write(f'Experiences:      {exp_count}')
        self.stdout.write(f'Certificates:     {cert_count}')
        self.stdout.write(f'Attestations:     {att_count}')
        self.stdout.write(f'Trust scores:     {ts_count}')
        self.stdout.write(f'Badges:           {badge_count}')
        self.stdout.write('')
        self.stdout.write(f'Login with any email @trustledger.demo / password: {PASSWORD}')