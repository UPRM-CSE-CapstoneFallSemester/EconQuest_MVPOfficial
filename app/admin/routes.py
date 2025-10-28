from datetime import datetime, timedelta
from flask import (
    render_template, abort, request, redirect, url_for,
    flash, jsonify, session as flask_session
)
from flask_login import login_required, current_user
from ..models import (
    Users, Modules, Activities, Attempts, AuthSession, db,
    ROLE_ADMIN, ROLE_TEACHER, ROLE_STUDENT
)
from sqlalchemy import and_

try:
    from ..models import Groups, GroupMembers, ModuleAssignments
except Exception:
    Groups = GroupMembers = ModuleAssignments = None

try:
    from ..models import UserProfile
except Exception:
    UserProfile = None

try:
    from ..models import GameSettings
except Exception:
    GameSettings = None

try:
    from .. import csrf
except Exception:
    csrf = None

from . import admin_bp

from ..models import (
    db, Users, Modules, Activities, Attempts, AuthSession,
    ROLE_ADMIN, ROLE_TEACHER, ROLE_STUDENT
)

try:
    from ..models import GameSettings
except Exception:
    GameSettings = None

# --- imports arriba del archivo (añade si faltan) ---
from sqlalchemy import and_

# intenta traer tablas opcionales para el Data Browser
try:
    from ..models import Groups, GroupMembers, ModuleAssignments
except Exception:
    Groups = GroupMembers = ModuleAssignments = None

try:
    from ..models import UserProfile
except Exception:
    UserProfile = None

try:
    from ..models import GameSettings
except Exception:
    GameSettings = None

try:
    from ..models import RequestLog
except Exception:
    RequestLog = None


ALLOWED_MODELS = {
    "users": Users,
    "modules": Modules,
    "activities": Activities,
    "attempts": Attempts,
    "auth_sessions": AuthSession,
}
if GameSettings:
    ALLOWED_MODELS["game_settings"] = GameSettings
if Groups:
    ALLOWED_MODELS["groups"] = Groups
if GroupMembers:
    ALLOWED_MODELS["group_members"] = GroupMembers
if ModuleAssignments:
    ALLOWED_MODELS["module_assignments"] = ModuleAssignments
if UserProfile:
    ALLOWED_MODELS["user_profiles"] = UserProfile
if RequestLog:
    # Solo lectura de logs (no hay campos editables)
    ALLOWED_MODELS["request_log"] = RequestLog


# Helpers
def is_admin() -> bool:
    return current_user.is_authenticated and current_user.role == ROLE_ADMIN


def _get_settings():
    """
    Obtiene (o crea) la fila única de GameSettings.
    Si el modelo no existe, devuelve None.
    """
    if not GameSettings:
        return None
    s = GameSettings.query.get(1)
    if not s:
        s = GameSettings(id=1, xp_base=100, xp_growth=50, max_attempts_default=3)
        db.session.add(s)
        db.session.commit()
    return s


# Guards
@admin_bp.before_request
def guard():
    if not current_user.is_authenticated:
        return abort(401)

    if request.endpoint == "admin.api_ping":
        return

    if not is_admin():
        return abort(403)



# Dashboard
@admin_bp.route("/dashboard")
@login_required
def dashboard():
    # --- existing counts ---
    total_users = Users.query.count()
    total_students = Users.query.filter_by(role=ROLE_STUDENT).count()
    total_teachers = Users.query.filter_by(role=ROLE_TEACHER).count()

    modules_count = Modules.query.count()
    published_mod = Modules.query.filter_by(is_published=True).count() if hasattr(Modules, "is_published") else 0
    activities_ct = Activities.query.count()
    attempts_ct = Attempts.query.count()

    # --- NEW: live metrics (last 60 minutes) ---
    from ..models import RequestLog  # local import to avoid circulars
    window_start = datetime.utcnow() - timedelta(hours=1)

    # availability = % of successful (status < 500) among all requests in window
    total_reqs = RequestLog.query.filter(RequestLog.created_at >= window_start).count()
    ok_reqs = RequestLog.query.filter(
        and_(RequestLog.created_at >= window_start, RequestLog.status_code < 500)
    ).count()
    availability_pct = (ok_reqs / total_reqs * 100.0) if total_reqs else 100.0

    # p95 for /student/dashboard (you can change the path if you prefer)
    q = (RequestLog.query
         .filter(and_(RequestLog.created_at >= window_start,
                      RequestLog.path == "/student/dashboard",
                      RequestLog.status_code < 500))
         .with_entities(RequestLog.duration_ms)
         .order_by(RequestLog.duration_ms.asc()))
    durations = [r.duration_ms for r in q.all()]
    if durations:
        # simple percentile calc (no numpy): pick the 95th index
        k = int(0.95 * (len(durations) - 1))
        p95_ms = durations[k]
    else:
        p95_ms = 0

    stats = {
        "total_users": total_users,
        "students": total_students,
        "teachers": total_teachers,
        "modules": modules_count,
        "published": published_mod,
        "activities": activities_ct,
        "attempts": attempts_ct,

        # Replaces the hard-coded strings
        "availability_pct": availability_pct,  # float
        "p95_ms": p95_ms,                      # int milliseconds
    }

    cutoff = datetime.utcnow() - timedelta(minutes=2)
    online = (AuthSession.query
              .filter_by(active=True)
              .filter(AuthSession.last_seen >= cutoff)
              .count())

    recent_users = Users.query.order_by(Users.created_at.desc()).limit(8).all()
    settings = _get_settings()
    modules = Modules.query.order_by(Modules.id.desc()).all()
    recent_activities = Activities.query.order_by(Activities.id.desc()).limit(20).all()

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        online=online,
        recent_users=recent_users,
        settings=settings,
        modules=modules,
        recent_activities=recent_activities,
        ALLOWED_MODELS=ALLOWED_MODELS,
    )


# Live Sessions (vista + API)
@admin_bp.route("/sessions")
@login_required
def sessions_live():
    return render_template("admin/sessions.html")


@admin_bp.route("/api/active-sessions")
@login_required
def api_active_sessions():
    cutoff = datetime.utcnow() - timedelta(minutes=5)
    rows = (
        AuthSession.query
        .filter(AuthSession.active == True, AuthSession.last_seen >= cutoff)
        .order_by(AuthSession.last_seen.desc())
        .limit(200)
        .all()
    )
    data = []
    for s in rows:
        data.append({
            "id": s.id,
            "user_id": s.user_id,
            "name": getattr(s.user, "name", ""),
            "role": getattr(s.user, "role", ""),
            "email": getattr(s.user, "email", ""),
            "login_at": s.login_at.isoformat(timespec="seconds") if s.login_at else None,
            "last_seen": s.last_seen.isoformat(timespec="seconds") if s.last_seen else None,
            "ip": getattr(s, "ip", None),
        })
    return jsonify(data)


if csrf:
    @admin_bp.route("/api/ping", methods=["POST", "GET"])
    @csrf.exempt
    @login_required
    def api_ping():
        now = datetime.utcnow()
        ip  = request.headers.get("X-Forwarded-For", request.remote_addr)

        sid = flask_session.get("auth_session_id")
        s = AuthSession.query.get(sid) if sid else None

        if not s:
            s = AuthSession(
                user_id=current_user.id,
                login_at=now,
                last_seen=now,
                ip=ip,
                active=True,
            )
            db.session.add(s)
            db.session.commit()
            flask_session["auth_session_id"] = s.id
        else:
            s.last_seen = now
            s.active = True
            if not s.ip:
                s.ip = ip
            db.session.commit()

        return ("", 204)
else:
    @admin_bp.route("/api/ping", methods=["POST", "GET"])
    @login_required
    def api_ping():
        now = datetime.utcnow()
        ip  = request.headers.get("X-Forwarded-For", request.remote_addr)

        sid = flask_session.get("auth_session_id")
        s = AuthSession.query.get(sid) if sid else None

        if not s:
            s = AuthSession(
                user_id=current_user.id,
                login_at=now,
                last_seen=now,
                ip=ip,
                active=True,
            )
            db.session.add(s)
            db.session.commit()
            flask_session["auth_session_id"] = s.id
        else:
            s.last_seen = now
            s.active = True
            if not s.ip:
                s.ip = ip
            db.session.commit()

        return ("", 204)



@admin_bp.route("/data")
@login_required
def data_home():
    return render_template("admin/data_home.html", models=ALLOWED_MODELS)


@admin_bp.route("/data/<model>", methods=["GET", "POST"])
@login_required
def data_table(model):
    if model not in ALLOWED_MODELS:
        return abort(404)
    Model = ALLOWED_MODELS[model]

    editable = {
        "users": ["name", "email", "role", "locale"],
        "modules": ["title", "summary", "is_published", "level", "xp_reward"],
        "activities": ["title", "type", "max_points", "module_id", "position",
                       "is_published", "attempt_limit", "default_xp", "content_json"],
        "attempts": ["score"],
        "groups": ["name", "teacher_id", "grade_level", "section"] if Groups else [],
        "group_members": ["group_id", "user_id"] if GroupMembers else [],
        "module_assignments": ["module_id", "target_type", "target_id"] if ModuleAssignments else [],
        "user_profiles": ["credit_score", "cash_balance", "salary_monthly", "has_car",
                          "car_payment_monthly", "level", "xp", "energy"] if UserProfile else [],
        "game_settings": ["xp_base", "xp_growth", "max_attempts_default"] if GameSettings else [],
        "auth_sessions": ["active"],  #  mín
    }

    if request.method == "POST":
        _ = request.form.get("csrf_token")
        action = request.form.get("action")
        if action == "delete":
            rid = int(request.form.get("id"))
            row = Model.query.get_or_404(rid)
            db.session.delete(row)
            db.session.commit()
            flash("Registro eliminado.", "success")
            return redirect(url_for("admin.data_table", model=model))
        elif action == "save":
            rid = request.form.get("id")
            if rid:
                row = Model.query.get_or_404(int(rid))
            else:
                row = Model()
                db.session.add(row)

            allowed = editable.get(model, [])
            for f in allowed:
                if f in request.form:
                    val = request.form.get(f)

                    coltype = getattr(Model, f).type.__class__.__name__.lower()
                    if "integer" in coltype:
                        val = int(val) if val not in (None, "",) else None
                    elif "boolean" in coltype:
                        # checkboxes llegan como "on" si están marcados
                        val = val in ("1", "true", "on", "True", "on")
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


# Users (roles)
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


# Settings (Game Settings)
@admin_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings_view():
    settings = _get_settings()
    if GameSettings is None:
        flash("GameSettings no está definido en modelos o migraciones.", "error")
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        _ = request.form.get("csrf_token")
        try:
            xp_base = int(request.form.get("xp_base", "100") or 100)
            xp_growth = int(request.form.get("xp_growth", "50") or 50)
            max_attempts_default = int(request.form.get("max_attempts_default", "3") or 3)

            settings.xp_base = xp_base
            settings.xp_growth = xp_growth
            settings.max_attempts_default = max_attempts_default
            settings.updated_at = datetime.utcnow()
            db.session.commit()
            flash("Configuración actualizada.", "success")
            return redirect(url_for("admin.settings_view"))
        except Exception:
            db.session.rollback()
            flash("No se pudo actualizar la configuración.", "error")


    # Render
    return render_template("admin/settings.html", settings=settings)
