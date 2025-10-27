"""App factory para EconQuest (Flask)."""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_jwt_extended import JWTManager
from .config import Config
from time import perf_counter
from flask import g, request


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
jwt = JWTManager()

def create_app(config_object: type = Config) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_object)
    db.init_app(app); migrate.init_app(app, db)
    login_manager.init_app(app); csrf.init_app(app); jwt.init_app(app)
    login_manager.login_view = "auth.login"

    from .auth.routes import auth_bp
    from .main.routes import main_bp
    from .student.routes import student_bp
    from .teacher.routes import teacher_bp
    from .admin.routes import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(student_bp, url_prefix="/student")
    app.register_blueprint(teacher_bp, url_prefix="/teacher")
    app.register_blueprint(admin_bp, url_prefix="/admin")



    @app.cli.command("seed")
    def seed_command():
        from .seed import run_seed; run_seed(); print("Seed listo.")

    @app.cli.command("reset-db")
    def reset_db_command():
        """
        Dev only: resetea la base.
        - Si es SQLite, borra el archivo y crea tablas.
        - Luego corre el seed.
        """
        import os
        from pathlib import Path
        uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        if uri.startswith("sqlite:///"):
            db_path = uri.replace("sqlite:///", "")
            p = Path(db_path)
            if p.exists():
                p.unlink()
            with app.app_context():
                db.create_all()
                from .seed import run_seed
                run_seed()
            print(f"Base SQLite recreada en {db_path} y seed cargado.")
        else:
            # Fallback para otros engines en dev: drop_all/create_all (sin migraciones)
            with app.app_context():
                db.drop_all()
                db.create_all()
                from .seed import run_seed
                run_seed()
            print("Base recreada (drop_all/create_all) y seed cargado.")

    @app.before_request
    def _rq_start():
        g._rq_t0 = perf_counter()

    @app.after_request
    def _rq_stop(response):
        """Record duration/status for non-static requests so the admin dashboard can compute p95 & availability."""
        try:
            # Skip static files and the admin heartbeat to avoid noise
            if request.path.startswith("/static") or request.endpoint in ("admin.api_ping",):
                return response

            t0 = getattr(g, "_rq_t0", None)
            if t0 is None:
                return response

            duration_ms = int((perf_counter() - t0) * 1000)

            # Import lazily to avoid circulars on app init
            from app.models import RequestLog, db  # type: ignore
            rec = RequestLog(
                method=request.method,
                path=request.path[:180],
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
            db.session.add(rec)
            db.session.commit()
        except Exception:
            # Never break a response because of metrics
            try:
                from app.models import db  # type: ignore
                db.session.rollback()
            except Exception:
                pass
        return response

    return app

