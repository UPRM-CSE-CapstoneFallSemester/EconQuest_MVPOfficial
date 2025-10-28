# locustfile.py
"""
EconQuest Locust test (resilient) con POST de actividad correcto.
- Hace login por formulario (CSRF) y por JWT.
- Para /student/activity/<id>:
  GET (extrae csrf + radios q0,q1,...) -> POST con respuestas válidas.
Env:
  ECONQUEST_HOST, LOCUST_EMAIL, LOCUST_PASSWORD
"""

import os
import re
import random
from bs4 import BeautifulSoup  # pip install beautifulsoup4
from locust import HttpUser, task, between

ECONQUEST_HOST = os.getenv("ECONQUEST_HOST", "http://localhost:5000")
LOCUST_EMAIL = os.getenv("LOCUST_EMAIL", "student@econquest.local")
LOCUST_PASSWORD = os.getenv("LOCUST_PASSWORD", "student123")

# Regex tolerantes para CSRF en formularios
RE_CSRF_A = re.compile(r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']', re.I)
RE_CSRF_B = re.compile(r'value=["\']([^"\']+)["\'][^>]*name=["\']csrf_token["\']', re.I)
RE_ACTIVITY_LINK = re.compile(r'href="/student/activity/(\d+)"')

def extract_csrf(html: str):
    m = RE_CSRF_A.search(html) or RE_CSRF_B.search(html)
    return m.group(1) if m else None

def extract_questions_and_csrf(html: str):
    """Devuelve (csrf, form_dict) donde form_dict tiene q0,q1,... con 1 opción cada una."""
    soup = BeautifulSoup(html, "html.parser")
    # CSRF
    token = None
    tok_input = soup.select_one('input[name="csrf_token"]')
    if tok_input and tok_input.get("value"):
        token = tok_input["value"]
    if not token:
        token = extract_csrf(html)

    # Preguntas q0, q1...
    # Tomamos la PRIMERA opción disponible por pregunta (rápido y suficiente para la prueba)
    answers = {}
    radios = soup.select('input[type="radio"][name^="q"]')
    if radios:
        # agrupar por nombre
        by_name = {}
        for r in radios:
            nm = r.get("name")
            if not nm:
                continue
            by_name.setdefault(nm, []).append(r)
        for nm, opts in by_name.items():
            # elige una opción "al azar" para simular variedad
            choice = random.choice(opts)
            if choice and choice.get("value") is not None:
                answers[nm] = choice["value"]

    return token, answers

class EconQuestUser(HttpUser):
    host = ECONQUEST_HOST
    wait_time = between(1, 3)

    token = None
    session_ok = False

    def on_start(self):
        # 1) Intento de login por formulario (sesión Flask-Login)
        try:
            r = self.client.get("/auth/login", name="/auth/login (GET)", allow_redirects=True)
            csrf = extract_csrf(r.text)
            if csrf:
                payload = {"email": LOCUST_EMAIL, "password": LOCUST_PASSWORD, "csrf_token": csrf}
                res = self.client.post("/auth/login", data=payload, name="/auth/login (POST)", allow_redirects=True)
                if res.status_code in (200, 302):
                    self.session_ok = True
            else:
                print("[locust] CSRF no encontrado en /auth/login; se continúa sin cookie de sesión.")
        except Exception as e:
            print(f"[locust] Excepción login formulario: {e}")

        # 2) JWT para /auth/api/*
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
                    print("[locust] /auth/api/login sin JSON o sin access_token.")
        except Exception as e:
            print(f"[locust] Excepción JWT login: {e}")

    def _auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(2)
    def view_home(self):
        self.client.get("/", name="/")

    @task(3)
    def view_student_dashboard(self):
        if self.session_ok:
            self.client.get("/student/dashboard", name="/student/dashboard")
        else:
            if self.token:
                self.client.get("/auth/api/me", headers=self._auth_headers(), name="/auth/api/me (fallback)")

    @task(1)
    def api_me(self):
        if self.token:
            self.client.get("/auth/api/me", headers=self._auth_headers(), name="/auth/api/me")

    @task(3)
    def play_activity(self):
        """Flujo completo GET->POST con CSRF y respuestas q*.
           - intenta descubrir un activity_id desde el dashboard
           - fallback a un ID fijo si no encuentra
        """
        if not self.session_ok:
            return  # sin sesión de Flask-Login, el POST fallará por CSRF

        # Descubrir una actividad desde el dashboard del alumno (si existe)
        act_id = None
        try:
            dash = self.client.get("/student/dashboard", name="/student/dashboard (harvest)")
            m = RE_ACTIVITY_LINK.findall(dash.text)
            if m:
                act_id = random.choice(m)  # elige una de las actividades listadas
        except Exception:
            pass

        if not act_id:
            act_id = "2"  # <- fallback; cambia si lo necesitas

        # GET actividad (para obtener csrf + radios q*)
        r = self.client.get(f"/student/activity/{act_id}", name="/student/activity/<id> (GET)")
        csrf, answers = extract_questions_and_csrf(r.text)
        if not csrf or not answers:
            # evita 400 por datos incompletos
            return

        answers["csrf_token"] = csrf

        # POST con respuestas
        # permitimos redirect (la vista suele redirigir a /student/activities/<id>/result)
        self.client.post(
            f"/student/activity/{act_id}",
            data=answers,
            name="/student/activity/<id> (POST)",
            allow_redirects=True
        )
