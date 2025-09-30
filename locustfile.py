# locustfile.py
"""
EconQuest Locust test (resilient).
- Tries Flask-Login form (CSRF) to get a session cookie for /student/dashboard.
- If CSRF or form login fails, it keeps running with JWT/public endpoints so the test does NOT end.
- Minimal, beginner-friendly code and comments.

Env:
  ECONQUEST_HOST       default: http://localhost:5000
  LOCUST_EMAIL         default: student@econquest.local
  LOCUST_PASSWORD      default: student123
"""

import os
import re
from locust import HttpUser, task, between

ECONQUEST_HOST = os.getenv("ECONQUEST_HOST", "http://localhost:5000")
LOCUST_EMAIL = os.getenv("LOCUST_EMAIL", "student@econquest.local")
LOCUST_PASSWORD = os.getenv("LOCUST_PASSWORD", "student123")

# Regex tolerant to attribute order/spaces/quotes:
RE_CSRF_A = re.compile(r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']', re.I)
RE_CSRF_B = re.compile(r'value=["\']([^"\']+)["\'][^>]*name=["\']csrf_token["\']', re.I)

def extract_csrf(html: str):
    m = RE_CSRF_A.search(html) or RE_CSRF_B.search(html)
    return m.group(1) if m else None


class EconQuestUser(HttpUser):
    host = ECONQUEST_HOST
    wait_time = between(1, 3)

    # State
    token = None            # JWT for /auth/api/*
    session_ok = False      # True if Flask-Login cookie established

    def on_start(self):
        """Try to establish both a Flask-Login session and a JWT token. Never StopUser."""
        # 1) Try HTML form login (needs CSRF)
        try:
            r = self.client.get("/auth/login", name="/auth/login (GET)", allow_redirects=True)
            csrf = extract_csrf(r.text)
            if not csrf:
                # Don’t stop. Just log once per user.
                # (You can comment this print if it’s too chatty.)
                print("[locust] CSRF not found on /auth/login (will proceed without session cookie).")
            else:
                payload = {"email": LOCUST_EMAIL, "password": LOCUST_PASSWORD, "csrf_token": csrf}
                res = self.client.post("/auth/login", data=payload, name="/auth/login (POST)", allow_redirects=True)
                if res.status_code in (200, 302):
                    self.session_ok = True
                else:
                    print(f"[locust] Form login failed: status={res.status_code}")
        except Exception as e:
            print(f"[locust] Exception during form login: {e}")

        # 2) JWT login (for /auth/api/*)
        try:
            api = self.client.post(
                "/auth/api/login",
                json={"email": LOCUST_EMAIL, "password": LOCUST_PASSWORD},
                name="/auth/api/login"
            )
            if api.status_code == 200:
                try:
                    self.token = api.json().get("access_token")
                except Exception:
                    self.token = None
                    print("[locust] /auth/api/login returned non-JSON or missing access_token.")
            else:
                print(f"[locust] /auth/api/login failed: status={api.status_code}")
        except Exception as e:
            print(f"[locust] Exception during JWT login: {e}")

        # Note: We NEVER raise StopUser here. The run will continue no matter what.

    def _auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(2)
    def view_home(self):
        # Public page – always safe
        self.client.get("/", name="/")

    @task(3)
    def view_student_dashboard(self):
        # Only hit dashboard if we have a Flask-Login session cookie from the form login.
        if self.session_ok:
            self.client.get("/student/dashboard", name="/student/dashboard")
        else:
            # Fall back to a lightweight authenticated API call (or noop if no JWT)
            if self.token:
                self.client.get("/auth/api/me", headers=self._auth_headers(), name="/auth/api/me (fallback)")

    @task(1)
    def api_me(self):
        # Pure API path (JWT). If there’s no token, this becomes a noop.
        if self.token:
            self.client.get("/auth/api/me", headers=self._auth_headers(), name="/auth/api/me")
