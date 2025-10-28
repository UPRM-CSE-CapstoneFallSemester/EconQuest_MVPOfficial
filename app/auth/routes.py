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
from werkzeug.security import check_password_hash

def _record_login(user):
    now = datetime.utcnow()
    ip  = request.headers.get("X-Forwarded-For", request.remote_addr)

    s = AuthSession(
        user_id=user.id,
        login_at=now,
        last_seen=now,
        ip=ip,
        active=True,
    )
    # si tu modelo tiene user_agent, se llena; si no, no pasa nada
    if hasattr(s, "user_agent"):
        s.user_agent = (request.headers.get("User-Agent") or "")[:255]

    db.session.add(s)
    db.session.commit()
    flask_session["auth_session_id"] = s.id

def _record_logout():
    sid = flask_session.pop("auth_session_id", None)
    if not sid:
        return
    s = AuthSession.query.get(sid)
    if not s:
        return
    s.active = False
    s.last_seen = datetime.utcnow()
    if hasattr(s, "logout_at"):
        s.logout_at = datetime.utcnow()
    db.session.commit()

def _redirect_by_role(user):
    role = (user.role or "student").strip().lower()
    if role == "admin":
        return redirect(url_for("admin.dashboard"))
    elif role == "teacher":
        return redirect(url_for("teacher.dashboard"))
    else:
        return redirect(url_for("student_ui.dashboard"))

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return _redirect_by_role(current_user)

    form = RegisterForm()

    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if Users.query.filter_by(email=email).first():
            form.email.errors.append("Ese email ya está registrado.")
            flash("No se pudo crear la cuenta. Corrige los campos marcados y vuelve a intentar.", "error")
            return render_template("auth/register.html", form=form)

        # Crear y auto-login
        user = Users(
            name=form.name.data.strip(),
            email=email,
            role=ROLE_STUDENT,
            locale="es",
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        login_user(user, remember=False)
        try:
            _record_login(user)  # si tienes esta función
        except Exception:
            pass

        flash("¡Cuenta creada y sesión iniciada!", "success")
        return _redirect_by_role(user)

    # POST pero inválido: explica por qué
    if request.method == "POST":
        reasons = []
        for field in (form.name, form.email, form.password, form.confirm, form.csrf_token):
            for err in field.errors:
                reasons.append(f"{field.label.text}: {err}")
        if reasons:
            flash("No se pudo crear la cuenta. " + " | ".join(reasons), "error")
        else:
            flash("No se pudo crear la cuenta. Revisa los campos.", "error")

    return render_template("auth/register.html", form=form)



@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        # Ya logueado: manda por rol
        role = (current_user.role or "student").strip().lower()
        if role == "admin":
            return redirect(url_for("admin.dashboard"))
        elif role == "teacher":
            return redirect(url_for("teacher.dashboard"))
        else:
            return redirect(url_for("student_ui.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        email = (form.email.data or "").strip().lower()
        user = Users.query.filter_by(email=email).first()

        if user and check_password_hash(user.hashed_pw, form.password.data):
            # Normaliza y persiste role por si estuviera con mayúsculas/espacios
            user.role = (user.role or "student").strip().lower()
            db.session.commit()

            login_user(user, remember=getattr(form, "remember_me", False))
            if user and check_password_hash(user.hashed_pw, form.password.data):
                user.role = (user.role or "student").strip().lower()
                db.session.commit()

                login_user(user, remember=getattr(form, "remember_me", False))
                _record_login(user)  # <---- IMPORTANTE

                nxt = request.args.get("next")
                if nxt:
                    return redirect(nxt)
                if user.role == "admin":
                    return redirect(url_for("admin.dashboard"))
                elif user.role == "teacher":
                    return redirect(url_for("teacher.dashboard"))
                else:
                    return redirect(url_for("student_ui.dashboard"))

            # Respeta ?next si viene de @login_required
            nxt = request.args.get("next")
            if nxt:
                return redirect(nxt)

            if user.role == "admin":
                return redirect(url_for("admin.dashboard"))
            elif user.role == "teacher":
                return redirect(url_for("teacher.dashboard"))
            else:
                return redirect(url_for("student_ui.dashboard"))
        else:
            flash("Invalid email or password.", "error")

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

