import json
from . import db
from .models import (
    Users, Modules, Activities,
    ROLE_ADMIN, ROLE_TEACHER, ROLE_STUDENT,
    StudentProfile, GameSettings
)

def ensure_student_profile(email, **kwargs):
    u = Users.query.filter_by(email=email).first()
    if not u:
        return
    if not u.profile:
        sp = StudentProfile(user_id=u.id, **kwargs)
        db.session.add(sp)
        db.session.commit()

def run_seed():
    # Usuarios demo
    if not Users.query.filter_by(email="admin@econquest.test").first():
        admin = Users(name="Admin", email="admin@econquest.test",
                      role=ROLE_ADMIN, locale="es")
        admin.set_password("admin123")
        db.session.add(admin)

    if not Users.query.filter_by(email="teacher@econquest.local").first():
        t = Users(name="Profe Budget", email="teacher@econquest.local",
                  role=ROLE_TEACHER, locale="es")
        t.set_password("teacher123")
        db.session.add(t)

    if not Users.query.filter_by(email="student@econquest.local").first():
        s = Users(name="Estu Demo", email="student@econquest.local",
                  role=ROLE_STUDENT, locale="es")
        s.set_password("student123")
        db.session.add(s)

    # Módulo demo con actividades
    if not Modules.query.filter_by(title="Budgeting Básico").first():
        m = Modules(
            title="Budgeting Básico",
            summary="Introducción a conceptos básicos de presupuesto.",
            level=1,
            xp_reward=100,
            is_published=True
        )
        db.session.add(m)
        db.session.flush()  # asegura m.id

        a1 = Activities(
            module_id=m.id,
            type="scenario",
            max_points=100,
            position=1,
            title="Escenario inicial",
            is_published=True,
            content_json=json.dumps({
                "prompt": "Tienes $1000 al mes. ¿Qué haces primero?",
                "options": [
                    {"label": "Separar 10% ahorro y pagar renta", "delta": 15},
                    {"label": "Comprar un celular nuevo a crédito", "delta": -10}
                ]
            })
        )

        a2 = Activities(
            module_id=m.id,
            type="quiz",
            max_points=100,
            position=2,
            title="Concepto de gasto fijo",
            is_published=True,
            content_json=json.dumps({
                "prompt": "¿Qué es un gasto fijo?",
                "options": [
                    {"label": "Pago de renta mensual", "delta": 10},
                    {"label": "Comer afuera", "delta": -5}
                ]
            })
        )

        db.session.add_all([a1, a2])

    db.session.commit()

    # Perfiles demo
    ensure_student_profile(
        "student@econquest.local",
        credit_score=620, cash_balance=500, salary_monthly=1600,
        has_car=True, car_payment_monthly=220, level=1, xp=0, energy=100
    )
    ensure_student_profile(
        "teacher@econquest.local",
        credit_score=650, cash_balance=800, salary_monthly=2200,
        has_car=False, car_payment_monthly=0, level=2, xp=50, energy=100
    )

    # Game settings
    if not GameSettings.query.get(1):
        s = GameSettings(id=1, xp_base=100, xp_growth=50, max_attempts_default=3)
        db.session.add(s)
        db.session.commit()
