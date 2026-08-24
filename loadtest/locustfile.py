"""Load test for Cursus — simulates the 3 roles' most common request mix.

Default target: local Docker Postgres/backend (see loadtest/README.md), NOT
Supabase or any real deployment. Locust's --host flag can point elsewhere,
but per docs/decisions/ADR.md (RLS/load-test ADR entry), that requires
explicit confirmation from the project owner first — never point this at
Railway/Supabase without asking.

Run:
    locust -f loadtest/locustfile.py --host http://localhost:8000

Headless, ~1000 concurrent users, 2 min, CSV output with p50/p95/p99:
    locust -f loadtest/locustfile.py --host http://localhost:8000 \
        --headless --users 1000 --spawn-rate 50 --run-time 2m \
        --csv loadtest/results/run1
"""

from __future__ import annotations

import random

from locust import HttpUser, between, task

# Demo roles seeded by scripts/provision_organization.py / demo fixtures —
# same 3 accounts the frontend's /demo/select-role screen uses.
_ROLES = ("student", "instructor", "admin")

_QA_QUESTIONS = (
    "What is required to pass SSA101?",
    "What happens in Session 1?",
    "How is the final grade calculated?",
    "What is a problem statement?",
    "Where do I start writing my stakeholder analysis?",
)


class CursusUser(HttpUser):
    """One simulated browser session. Weighted so the mix roughly matches
    real traffic: mostly students reading their plan and asking questions,
    occasionally an instructor checking alerts or an admin checking KPIs.
    """

    wait_time = between(1, 3)  # seconds between tasks, like a real user reading

    def on_start(self) -> None:
        self.role = random.choice(_ROLES)
        response = self.client.post(
            "/api/v1/auth/demo-session",
            json={"role": self.role},
            name="/auth/demo-session",
        )
        self.csrf_token = ""
        if response.ok:
            self.csrf_token = response.cookies.get("csrf_token", "")

    def _headers(self) -> dict[str, str]:
        return {"x-csrf-token": self.csrf_token} if self.csrf_token else {}

    @task(5)
    def view_weekly_plan(self) -> None:
        if self.role != "student":
            return
        self.client.get("/api/v1/plans/weekly", name="/plans/weekly")

    @task(4)
    def ask_curi(self) -> None:
        if self.role != "student":
            return
        self.client.post(
            "/api/v1/qa",
            json={
                "subjectCode": "SSA101",
                "question": random.choice(_QA_QUESTIONS),
            },
            headers=self._headers(),
            name="/qa",
        )

    @task(2)
    def view_reflections(self) -> None:
        if self.role != "student":
            return
        self.client.get("/api/v1/student/reflections", name="/student/reflections")

    @task(3)
    def instructor_alerts(self) -> None:
        if self.role != "instructor":
            return
        self.client.get("/api/v1/instructor/alerts", name="/instructor/alerts")

    @task(1)
    def admin_kpi(self) -> None:
        if self.role != "admin":
            return
        self.client.get("/api/v1/admin/kpi", name="/admin/kpi")

    @task(2)
    def whoami(self) -> None:
        # Cheapest possible authenticated request — a good baseline signal
        # for "is the auth/session layer itself the bottleneck".
        self.client.get("/api/v1/auth/me", name="/auth/me")
