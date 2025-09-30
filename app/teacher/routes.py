from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from ..models import db, Modules, Activities
from . import teacher_bp

def is_teacher_or_admin() -> bool:
    return current_user.is_authenticated and current_user.role in ("teacher","admin")

@teacher_bp.before_request
def guard():
    if not current_user.is_authenticated: return abort(401)
    if not is_teacher_or_admin(): return abort(403)

@teacher_bp.route("/dashboard")
@login_required
def dashboard():
    modules = Modules.query.order_by(Modules.created_at.desc()).all()
    return render_template("teacher/dashboard.html", modules=modules)

@teacher_bp.route("/modules/create", methods=["GET","POST"])
@login_required
def create_module():
    if request.method == "POST":
        title = request.form.get("title","").strip()
        lang = request.form.get("lang","es")
        publish = request.form.get("publish") == "on"
        if not title:
            flash("Título es requerido.", "error")
            return render_template("teacher/create_module.html")
        m = Modules(title=title, lang=lang, is_published=publish)
        db.session.add(m); db.session.commit()
        flash("Módulo creado.", "success")
        return redirect(url_for("teacher.dashboard"))
    return render_template("teacher/create_module.html")

@teacher_bp.route("/activities/create", methods=["GET","POST"])
@login_required
def create_activity():
    if request.method == "POST":
        module_id = int(request.form.get("module_id"))
        a_type = request.form.get("type","scenario")
        max_points = int(request.form.get("max_points",100))
        config_json = {
            "prompt": request.form.get("prompt",""),
            "options": [
                {"label": request.form.get("opt_a","Opción A"), "delta": int(request.form.get("delta_a",10))},
                {"label": request.form.get("opt_b","Opción B"), "delta": int(request.form.get("delta_b",-5))},
            ],
        }
        act = Activities(module_id=module_id, type=a_type, max_points=max_points, config_json=config_json)
        db.session.add(act); db.session.commit()
        flash("Actividad creada.", "success")
        return redirect(url_for("teacher.dashboard"))
    modules = Modules.query.all()
    return render_template("teacher/create_activity.html", modules=modules)
