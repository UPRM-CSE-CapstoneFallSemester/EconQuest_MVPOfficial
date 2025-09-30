from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from ..models import db, Modules, Activities, Attempts
from . import student_bp
from datetime import datetime

@student_bp.route("/dashboard")
@login_required
def dashboard():
    modules = Modules.query.filter_by(is_published=True).all()
    activities = Activities.query.all()
    return render_template("student/dashboard.html", modules=modules, activities=activities)

@student_bp.route("/attempt/<int:activity_id>", methods=["POST"])
@login_required
def start_attempt(activity_id: int):
    payload = {"answer": request.form.get("answer",""), "ts": datetime.utcnow().isoformat()}
    attempt = Attempts(activity_id=activity_id, user_id=current_user.id, answers_json=payload, score=0.0)
    db.session.add(attempt); db.session.commit()
    flash("Intento registrado. Recibirás feedback inmediato en la próxima versión.", "success")
    return redirect(url_for("student.dashboard"))
