from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from . import auth_bp
from ..admin import admin_bp
from ..forms import LoginForm, RegisterForm
from ..models import db, Users, ROLE_STUDENT
from .. import csrf
from datetime import datetime, timedelta
from flask import session as flask_session, request
from ..models import AuthSession, db  # importa el modelo nuevo

def _record_login(user):
    s = AuthSession(
        user_id=user.id,
        ip=request.headers.get("X-Forwarded-For", request.remote_addr),
        user_agent=(request.headers.get("User-Agent") or "")[:255],
    )
    db.session.add(s); db.session.commit()
    flask_session["auth_session_id"] = s.id

def _record_logout():
    sid = flask_session.pop("auth_session_id", None)
    if sid:
        s = AuthSession.query.get(sid)
        if s and s.active:
            s.active = False
            s.logout_at = datetime.utcnow()
            db.session.commit()

@auth_bp.route("/register", methods=["GET","POST"])
def register():
    if current_user.is_authenticated: return redirect(url_for("main.index"))
    form = RegisterForm()
    if form.validate_on_submit():
        if Users.query.filter_by(email=form.email.data.lower()).first():
            flash("Ese email ya está registrado.", "error")
            return render_template("auth/register.html", form=form)
        user = Users(name=form.name.data.strip(), email=form.email.data.lower(),
                     role=ROLE_STUDENT, locale="es")
        user.set_password(form.password.data)
        db.session.add(user); db.session.commit()
        flash("Cuenta creada. Ahora puedes iniciar sesión.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)

@auth_bp.route("/login", methods=["GET","POST"])
def login():
    # si ya está autenticado, redirige por rol
    if current_user.is_authenticated:
        return redirect(url_for(
            "admin.dashboard" if current_user.role=="admin" else
            "teacher.dashboard" if current_user.role=="teacher" else
            "student.dashboard"
        ))

    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(email=form.email.data.lower()).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            _record_login(user)
            # redirige directo a dashboard según rol
            return redirect(url_for(
                "admin.dashboard" if user.role=="admin" else
                "teacher.dashboard" if user.role=="teacher" else
                "student.dashboard"
            ))
        flash("Credenciales inválidas.", "error")
    elif form.is_submitted():
        errs = "; ".join(f"{f}: {', '.join(msgs)}" for f, msgs in form.errors.items()) or "Error desconocido"
        flash(f"Formulario inválido: {errs}", "error")

    return render_template("auth/login.html", form=form)

@auth_bp.route("/logout")
def logout():
    _record_logout()
    if current_user.is_authenticated: logout_user()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("main.index"))

@auth_bp.route("/api/login", methods=["POST"])
@csrf.exempt
def api_login():
    data = request.get_json() or {}
    email = data.get("email","").lower(); password = data.get("password","")
    user = Users.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"msg":"invalid credentials"}), 401

    # 👇 identity como string; metadatos en additional_claims
    token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role, "name": user.name}
    )
    return jsonify(access_token=token)

@auth_bp.route("/api/me")
@csrf.exempt
@jwt_required()
def api_me():
    # 👇 identity vuelve como string; lo convertimos a int si quieres
    uid = int(get_jwt_identity())
    claims = get_jwt()
    return jsonify(id=uid, role=claims.get("role"), name=claims.get("name"))

