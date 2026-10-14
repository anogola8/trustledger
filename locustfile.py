"""Load testing for TrustLedger — public pages only."""
from locust import HttpUser, task, between, events
import random


# Real slugs from your DB
WORKER_SLUGS = [
    'abdul-abdi-3cb696',
    'abdul-ali-38ca4b',
    'abdul-ali-6cd8bb',
    'abdul-barasa-dcda30',
    'abdul-mohamed-9d3505',
]

# Real verification codes
VERIFY_CODES = [
    'TL-32HC8-SVD28',
    'TL-RB33A-N8PZN',
    'TL-ZWYRS-SAN87',
    'TL-DUUXW-2BCFZ',
    'TL-F64ZY-4J8FM',
]


class AnonymousVisitor(HttpUser):
    """Curious visitor browsing public pages."""
    wait_time = between(1, 3)
    weight = 3

    @task(5)
    def landing(self):
        self.client.get("/")

    @task(4)
    def explore(self):
        self.client.get("/workers/explore/")

    @task(3)
    def explore_filter_skill(self):
        self.client.get("/workers/explore/?skill=House%20Cleaning")

    @task(2)
    def explore_filter_trust(self):
        self.client.get("/workers/explore/?min_trust=60")

    @task(3)
    def public_portfolio(self):
        slug = random.choice(WORKER_SLUGS)
        self.client.get(f"/w/{slug}/portfolio/")

    @task(1)
    def verify_home(self):
        self.client.get("/verify/")


class Verifier(HttpUser):
    """Someone verifying an attestation code."""
    wait_time = between(0.5, 2)
    weight = 2

    @task
    def verify_code(self):
        code = random.choice(VERIFY_CODES)
        self.client.get(f"/verify/{code}/", allow_redirects=True)


class WorkerUser(HttpUser):
    """Logged-in worker browsing their dashboard (POST login without Django import)."""
    wait_time = between(2, 5)
    weight = 1

    def on_start(self):
        # Login via HTTP — no Django model imports
        self.client.post("/accounts/login/", {
            "username": "kevin.muthoni@trustledger.demo",
            "password": "Demo1234!",
        }, allow_redirects=True)

    @task(3)
    def dashboard(self):
        self.client.get("/dashboard/")

    @task(2)
    def portfolio(self):
        self.client.get("/workers/portfolio/")

    @task(1)
    def attestations(self):
        self.client.get("/attestations/")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("=" * 60)
    print(f"LOAD TEST STARTING against {environment.host}")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("=" * 60)
    print("LOAD TEST COMPLETE")
    stats = environment.stats.total
    print(f"  Total requests: {stats.num_requests}")
    print(f"  Failures:       {stats.num_failures} ({stats.fail_ratio*100:.2f}%)")
    print(f"  Avg latency:    {stats.avg_response_time:.0f} ms")
    print(f"  p95 latency:    {stats.get_response_time_percentile(0.95):.0f} ms")
    print(f"  p99 latency:    {stats.get_response_time_percentile(0.99):.0f} ms")
    print(f"  Max RPS:        {stats.total_rps:.1f}")
    print("=" * 60)