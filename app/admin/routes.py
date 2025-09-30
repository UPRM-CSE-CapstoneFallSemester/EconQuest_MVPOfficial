from datetime import datetime, timedelta
from flask import render_template, abort, request, redirect, url_for, flash, jsonify, session as flask_session
from flask_login import login_required, current_user
from ..models import Users, Modules, Activities, Attempts, AuthSession, db, ROLE_ADMIN, ROLE_TEACHER, ROLE_STUDENT
from . import admin_bp


def is_admin() -> bool:
    return current_user.is_authenticated and current_user.role == "admin"


@admin_bp.before_request
def guard():
    if not current_user.is_authenticated: return abort(401)
    if not is_admin(): return abort(403)


# ---- Dashboard
@admin_bp.route("/dashboard")
@login_required
def dashboard():
    total_users = Users.query.count()
    total_students = Users.query.filter_by(role=ROLE_STUDENT).count()
    total_teachers = Users.query.filter_by(role=ROLE_TEACHER).count()
    modules_count = Modules.query.count()
    published_mod = Modules.query.filter_by(is_published=True).count() if hasattr(Modules, "is_published") else 0
    activities_ct = Activities.query.count()
    attempts_ct = Attempts.query.count()

    stats = {
        "total_users": total_users,
        "students": total_students,
        "teachers": total_teachers,
        "modules": modules_count,
        "published": published_mod,
        "activities": activities_ct,
        "attempts": attempts_ct,
        "p95_target": "< 500 ms",
        "availability_target": "99% objetivo",
    }

    # activos en los últimos 2 minutos
    cutoff = datetime.utcnow() - timedelta(minutes=2)
    online = AuthSession.query.filter_by(active=True).filter(AuthSession.last_seen >= cutoff).count()

    recent_users = Users.query.order_by(Users.created_at.desc()).limit(8).all()
    return render_template("admin/dashboard.html", stats=stats, online=online, recent_users=recent_users)


# ---- Live Sessions (vista + API)
@admin_bp.route("/sessions")
@login_required
def sessions_live():
    return render_template("admin/sessions.html")


@admin_bp.route("/api/active-sessions")
@login_required
def api_active_sessions():
    cutoff = datetime.utcnow() - timedelta(minutes=5)
    rows = (AuthSession.query
            .filter(AuthSession.active == True, AuthSession.last_seen >= cutoff)
            .order_by(AuthSession.last_seen.desc())
            .limit(100).all())
    data = [{
        "id": s.id,
        "user_id": s.user_id,
        "name": s.user.name,
        "role": s.user.role,
        "email": s.user.email,
        "login_at": s.login_at.isoformat(timespec="seconds"),
        "last_seen": s.last_seen.isoformat(timespec="seconds"),
        "ip": s.ip
    } for s in rows]
    return jsonify(data)


@admin_bp.route("/api/ping", methods=["POST"])
@login_required
def api_ping():
    sid = flask_session.get("auth_session_id")
    if sid:
        s = AuthSession.query.get(sid)
        if s and s.active:
            s.last_seen = datetime.utcnow()
            db.session.commit()
    return ("", 204)


# ---- Data Browser (lectura/edición segura)
ALLOWED_MODELS = {
    "users": Users,
    "modules": Modules,
    "activities": Activities,
    "attempts": Attempts,
}


@admin_bp.route("/data")
@login_required
def data_home():
    return render_template("admin/data_home.html", models=ALLOWED_MODELS)


@admin_bp.route("/data/<model>", methods=["GET", "POST"])
@login_required
def data_table(model):
    if model not in ALLOWED_MODELS: return abort(404)
    Model = ALLOWED_MODELS[model]

    if request.method == "POST":
        _ = request.form.get("csrf_token")
        action = request.form.get("action")
        if action == "delete":
            rid = int(request.form.get("id"))
            row = Model.query.get_or_404(rid)
            db.session.delete(row); db.session.commit()
            flash("Registro eliminado.", "success")
            return redirect(url_for("admin.data_table", model=model))
        elif action == "save":
            rid = request.form.get("id")
            if rid:
                row = Model.query.get_or_404(int(rid))
            else:
                row = Model(); db.session.add(row)

            allowed = {
                "users": ["name", "email", "role", "locale"],
                "modules": ["title", "description", "is_published"],
                "activities": ["title", "type", "max_points", "module_id"],
                "attempts": ["score"],
            }.get(model, [])

            for f in allowed:
                if f in request.form:
                    val = request.form.get(f)
                    col = getattr(Model, f).type.__class__.__name__.lower()
                    if "integer" in col:
                        val = int(val) if val not in (None, "",) else None
                    elif "boolean" in col:
                        val = val in ("1", "true", "on", "True")
                    setattr(row, f, val)

            db.session.commit()
            flash("Guardado.", "success")
            return redirect(url_for("admin.data_table", model=model))

    page = max(1, int(request.args.get("page", 1)))
    per  = 25
    pag  = Model.query.order_by(getattr(Model, "id").desc()).paginate(page=page, per_page=per, error_out=False)

    columns = [c.key for c in Model.__table__.columns]
    records = []
    for row in pag.items:
        d = {}
        for c in columns:
            d[c] = getattr(row, c)
        records.append(d)

    return render_template("admin/data_table.html", model=model, columns=columns, page=pag, records=records)


# ---- Users (roles) – mantén tu vista existente, o usa esta
@admin_bp.route("/users", methods=["GET", "POST"])
@login_required
def users_view():
    if request.method == "POST":
        _ = request.form.get("csrf_token")
        user_id = int(request.form.get("user_id", "0"))
        new_role = request.form.get("role", ROLE_STUDENT)
        if new_role not in (ROLE_STUDENT, ROLE_TEACHER, ROLE_ADMIN):
            flash("Rol inválido.", "error")
            return redirect(url_for("admin.users_view"))
        u = Users.query.get_or_404(user_id)
        if u.id == current_user.id and new_role != ROLE_ADMIN:
            flash("No puedes quitarte tu propio rol de admin.", "error")
            return redirect(url_for("admin.users_view"))
        u.role = new_role
        db.session.commit()
        flash("Rol actualizado.", "success")
        return redirect(url_for("admin.users_view"))

    users = Users.query.order_by(Users.created_at.desc()).all()
    roles = [ROLE_STUDENT, ROLE_TEACHER, ROLE_ADMIN]
    return render_template("admin/users.html", users=users, roles=roles)
