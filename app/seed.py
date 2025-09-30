from . import db
from .models import Users, Modules, Activities, ROLE_ADMIN, ROLE_TEACHER, ROLE_STUDENT
def run_seed():
    if not Users.query.filter_by(email="admin@econquest.test").first():
        admin = Users(name="Admin", email="admin@econquest.test", role=ROLE_ADMIN, locale="es")
        admin.set_password("admin123"); db.session.add(admin)
    if not Users.query.filter_by(email="teacher@econquest.local").first():
        t = Users(name="Profe Budget", email="teacher@econquest.local", role=ROLE_TEACHER, locale="es")
        t.set_password("teacher123"); db.session.add(t)
    if not Users.query.filter_by(email="student@econquest.local").first():
        s = Users(name="Estu Demo", email="student@econquest.local", role=ROLE_STUDENT, locale="es")
        s.set_password("student123"); db.session.add(s)
    if not Modules.query.filter_by(title="Budgeting Básico").first():
        m = Modules(title="Budgeting Básico", lang="es", is_published=True)
        db.session.add(m); db.session.flush()
        a1 = Activities(module_id=m.id, type="scenario", max_points=100,
            config_json={"prompt":"Tienes $1000 al mes. ¿Qué haces primero?",
                         "options":[{"label":"Separar 10% ahorro y pagar renta","delta":15},
                                    {"label":"Comprar un celular nuevo a crédito","delta":-10}]})
        a2 = Activities(module_id=m.id, type="quiz", max_points=100,
            config_json={"prompt":"¿Qué es un gasto fijo?",
                         "options":[{"label":"Pago de renta mensual","delta":10},
                                    {"label":"Comer afuera","delta":-5}]})
        db.session.add_all([a1,a2])
    db.session.commit()
