# app/student/routes.py
from datetime import datetime

from flask_login import login_required, current_user
from app import db
from app.models import Activities, Attempts, StudentProfile, Modules, GroupMembers, ModuleAssignments, GameSettings
import json

from flask import (
    Blueprint, render_template,
    request as flask_request,
    redirect, url_for, flash, abort,
    session as flask_session
)


# nombre único del blueprint (NO debe repetirse en otro archivo)
student_bp = Blueprint("student_ui", __name__, url_prefix="/student")
#                  ^^^^^^^^^^^

def _ensure_profile(u):
    # ya lo tienes en otras vistas; lo reutilizamos
    if not getattr(u, "profile", None):
        p = StudentProfile(
            user_id=u.id,
            credit_score=620,
            cash_balance=500,
            salary_monthly=1600,
            has_car=True,
            car_payment_monthly=220,
            level=1, xp=0, energy=100
        )
        db.session.add(p)
        db.session.commit()
        u.profile = p
    return u.profile

@student_bp.route("/modules")
@login_required
def modules_index():
    prof = _ensure_profile(current_user)

    # trae tus módulos como prefieras
    mods = Modules.query.order_by(Modules.id.asc()).all()

    # (opcional) progreso por módulo
    progress = {}
    for m in mods:
        total = len(m.activities)
        if total:
            done = (Attempts.query.filter_by(user_id=current_user.id)
                    .join(Activities)
                    .filter(Activities.module_id == m.id)
                    .count())
            progress[m.id] = int(done * 100 / total)
        else:
            progress[m.id] = 0

    return render_template(
        "student/modules.html",
        mods=mods,
        progress=progress,
        profile=prof,       # <-- ¡importante!
    )

@student_bp.route("/dashboard", endpoint="dashboard")
@login_required
def dashboard():
    """
    Student dashboard: muestra módulos asignados a los grupos del estudiante.
    Si no hay asignaciones, cae a módulos publicados. También lista actividades de esos módulos.
    """
    # --- 1) grupos del estudiante ---
    my_memberships = GroupMembers.query.filter_by(user_id=current_user.id).all()
    group_ids = [m.group_id for m in my_memberships]

    # --- 2) módulos asignados a esos grupos ---
    assigned_module_ids = []
    if group_ids:
        assigned_module_ids = [
            ma.module_id
            for ma in ModuleAssignments.query
                .filter(ModuleAssignments.group_id.in_(group_ids))
                .all()
        ]

    # --- 3) query de módulos a mostrar ---
    q = Modules.query
    if assigned_module_ids:
        q = q.filter(Modules.id.in_(assigned_module_ids))
    else:
        # fallback: publicados (o null)
        q = q.filter((Modules.is_published == True) | (Modules.is_published.is_(None)))

    # Orden seguro en SQLite: usa COALESCE para nulls primero/último
    modules = q.order_by(
        db.func.coalesce(Modules.level, 9999).asc(),
        Modules.id.desc()
    ).all()

    # --- 4) actividades de esos módulos (solo publicadas) ---
    activities = []
    if modules:
        mids = [m.id for m in modules]
        activities = (
            Activities.query
            .filter(Activities.module_id.in_(mids))
            .filter((Activities.is_published == True) | (Activities.is_published.is_(None)))
            .order_by(Activities.module_id.asc(), Activities.position.asc(), Activities.id.asc())
            .limit(10)
            .all()
        )

    return render_template("student/dashboard.html", modules=modules, activities=activities)

@student_bp.route("/missions")
@login_required
def missions():
    profile = _ensure_profile(current_user)
    return render_template("student/placeholder.html", title="Misiones", profile=profile)

@student_bp.route("/wallet")
@login_required
def wallet():
    profile = _ensure_profile(current_user)
    return render_template("student/placeholder.html", title="Billetera", profile=profile)

@student_bp.route("/badges")
@login_required
def badges():
    profile = _ensure_profile(current_user)
    return render_template("student/placeholder.html", title="Insignias", profile=profile)

@student_bp.route("/progress")
@login_required
def progress():
    profile = _ensure_profile(current_user)
    return render_template("student/placeholder.html", title="Progreso", profile=profile)

@student_bp.route("/help")
@login_required
def help_page():
    profile = _ensure_profile(current_user)
    return render_template("student/placeholder.html", title="Ayuda", profile=profile)


def _get_or_create_profile(user_id):
    prof = StudentProfile.query.filter_by(user_id=user_id).first()
    if not prof:
        prof = StudentProfile(user_id=user_id)
        db.session.add(prof)
        db.session.commit()
    return prof

def get_settings():
    s = GameSettings.query.get(1)
    if not s:
        s = GameSettings(id=1)
        db.session.add(s); db.session.commit()
    return s

def xp_needed_for_next(level:int, s:GameSettings) -> int:
    # simple arithmetic progression: base + growth*(level-1)
    return int((s.xp_base or 100) + (level - 1) * (s.xp_growth or 50))

@student_bp.route("/activity/<int:activity_id>", methods=["GET", "POST"], endpoint="play_activity")
@login_required
def play_activity(activity_id):
    a = Activities.query.get_or_404(activity_id)
    s = get_settings()
    atype = (a.type or "text").lower()

    # Limit logic
    used = Attempts.query.filter_by(user_id=current_user.id, activity_id=a.id).count()
    limit = a.attempt_limit if a.attempt_limit is not None else s.max_attempts_default
    blocked = (limit is not None) and (used >= limit)

    # Load content JSON (for quiz/scenario)
    content = {}
    if a.content_json:
        try: content = json.loads(a.content_json)
        except Exception: content = {}

    # If blocked, don't accept POST
    if blocked and flask_request.method == "POST":
        flash("Attempt limit reached for this activity.", "error")
        return redirect(url_for("student_ui.play_activity", activity_id=a.id))

    if flask_request.method == "POST":
        profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
        if not profile:
            profile = StudentProfile(user_id=current_user.id)
            db.session.add(profile)

        score = 0
        delta_credit = 0
        delta_cash = 0.0
        delta_energy = 0
        xp_gain = None
        answers = {}

        if atype in ("quiz","scenario"):
            for idx, q in enumerate(content.get("questions", [])):
                sel = flask_request.form.get(f"q{idx}")
                if sel is None: continue
                answers[str(idx)] = sel
                for opt in q.get("options", []):
                    if str(opt.get("key")) == str(sel):
                        score += int(opt.get("points", 0) or 0)
                        delta_credit += int(opt.get("delta_credit", 0) or 0)
                        delta_cash += float(opt.get("delta_cash", 0.0) or 0.0)
                        delta_energy += int(opt.get("delta_energy", 0) or 0)
                        if xp_gain is None and opt.get("xp") is not None:
                            xp_gain = int(opt["xp"])
                        break
        else:
            score = int(a.max_points or 0)
            xp_gain = a.default_xp or content.get("xp_reward") or a.max_points or 25

        if xp_gain is None:
            xp_gain = a.default_xp or content.get("xp_reward") or (a.max_points if a.max_points is not None else 25)

        # Apply effects
        if delta_credit:
            profile.credit_score = max(300, min(850, (profile.credit_score or 650) + delta_credit))
        if delta_cash:
            profile.cash_balance = (profile.cash_balance or 0.0) + delta_cash
        if delta_energy:
            profile.energy = max(0, (profile.energy or 100) + delta_energy)

        # XP + level up (xp stored as "progress within current level")
        level_ups = 0
        profile.xp = int((profile.xp or 0) + int(xp_gain))
        while True:
            need = xp_needed_for_next(int(profile.level or 1), s)
            if profile.xp >= need:
                profile.xp -= need
                profile.level = int(profile.level or 1) + 1
                level_ups += 1
            else:
                break

        # Save attempt with answers_json (NOT NULL)
        att = Attempts(
            user_id=current_user.id,
            activity_id=a.id,
            score=float(score),
            answers_json=json.dumps(answers),
            ended_at=datetime.utcnow(),
        )
        db.session.add(att)
        db.session.commit()

        flask_session["last_result"] = {
            "activity_id": a.id, "title": a.title, "score": int(score),
            "xp": int(xp_gain or 0), "delta_credit": int(delta_credit),
            "delta_cash": float(delta_cash), "delta_energy": int(delta_energy),
            "level_ups": int(level_ups),
            "attempts_left": (max(0, (limit - (used + 1))) if limit is not None else None)
        }
        return redirect(url_for("student_ui.activity_result", activity_id=a.id))

    # GET
    return render_template(
        "student/activity_quiz.html" if atype in ("quiz","scenario") else "student/activity_text.html",
        activity=a, content=content, attempts_used=used,
        attempts_left=(None if limit is None else max(0, limit - used)),
        attempt_limit=limit, blocked=blocked
    )


@student_bp.route("/activity/<int:activity_id>/result", methods=["GET"], endpoint="activity_result")
@login_required
def activity_result(activity_id):
    a = Activities.query.get_or_404(activity_id)
    payload = flask_session.pop("last_result", None)
    if not payload or payload.get("activity_id") != a.id:
        # if no result payload, go back
        return redirect(url_for("student_ui.dashboard"))
    return render_template("student/activity_result.html", activity=a, result=payload)

@student_bp.route("/module/<int:module_id>")
@login_required
def module_detail(module_id):
    module = Modules.query.get_or_404(module_id)
    activities = Activities.query.filter_by(
        module_id=module.id, is_published=True
    ).order_by(Activities.position.asc(), Activities.id.asc()).all()
    return render_template("student/module_detail.html",
                           module=module, activities=activities)




