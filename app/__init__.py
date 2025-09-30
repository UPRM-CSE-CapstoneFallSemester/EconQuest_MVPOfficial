"""App factory para EconQuest (Flask)."""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_jwt_extended import JWTManager
from .config import Config

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

    return app

