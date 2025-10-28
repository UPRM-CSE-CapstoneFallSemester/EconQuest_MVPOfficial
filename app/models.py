from datetime import datetime
from typing import Optional
from flask_login import UserMixin
from sqlalchemy.orm import backref

from . import db, login_manager
from werkzeug.security import generate_password_hash, check_password_hash

ROLE_STUDENT, ROLE_TEACHER, ROLE_ADMIN = "student","teacher","admin"
LOCALE_ES, LOCALE_EN = "es","en"

class Users(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    role = db.Column(db.String(16), nullable=False, default=ROLE_STUDENT)
    locale = db.Column(db.String(4), nullable=False, default=LOCALE_ES)
    hashed_pw = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    classes_taught = db.relationship("Classes", backref="teacher", lazy=True)
    def set_password(self, raw): self.hashed_pw = generate_password_hash(raw)
    def check_password(self, raw): return check_password_hash(self.hashed_pw, raw)
    def get_id(self): return str(self.id)

@login_manager.user_loader
def load_user(user_id: str) -> Optional["Users"]:
    return Users.query.get(int(user_id))

# --- Lightweight request metrics (for admin dashboard) ---
class RequestLog(db.Model):
    __tablename__ = "request_log"
    id = db.Column(db.Integer, primary_key=True)
    method = db.Column(db.String(8), nullable=False)
    path = db.Column(db.String(180), nullable=False, index=True)
    status_code = db.Column(db.Integer, nullable=False)
    duration_ms = db.Column(db.Integer, nullable=False)  # rounded ms
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<RequestLog {self.method} {self.path} {self.status_code} {self.duration_ms}ms>"


class Classes(db.Model):
    __tablename__ = "classes"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    code = db.Column(db.String(32), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Enrollments(db.Model):
    __tablename__ = "enrollments"
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    enrolled_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint("class_id","user_id", name="uq_enrollments_class_user"),)


class Attempts(db.Model):
    __tablename__ = "attempts"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"))
    activity_id = db.Column(db.Integer, db.ForeignKey("activities.id", ondelete="CASCADE"))
    score = db.Column(db.Float)
    # Make sure these exist in your model, because the DB has NOT NULL for answers_json
    answers_json = db.Column(db.Text, nullable=False, default="{}")
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("Users", lazy="joined")
    activity = db.relationship("Activities", lazy="joined")




class ScoreEvents(db.Model):
    __tablename__ = "score_events"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    activity_id = db.Column(db.Integer, db.ForeignKey("activities.id", ondelete="CASCADE"), nullable=False)
    delta = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(160))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Badges(db.Model):
    __tablename__ = "badges"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False, unique=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    criteria_json = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class UserBadges(db.Model):
    __tablename__ = "user_badges"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    badge_id = db.Column(db.Integer, db.ForeignKey("badges.id", ondelete="CASCADE"), nullable=False)
    awarded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint("user_id","badge_id", name="uq_user_badges_user_badge"),)

class AuthSession(db.Model):
    __tablename__ = "auth_sessions"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    login_at   = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    logout_at  = db.Column(db.DateTime)
    last_seen  = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    ip         = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    active     = db.Column(db.Boolean, default=True, nullable=False, index=True)

    user = db.relationship("Users", backref=db.backref("sessions", lazy="dynamic"))

    def mark_seen(self):
        self.last_seen = datetime.utcnow()

    @property
    def daily_income(self) -> int:
        return int((self.salary_monthly or 0) / 30)

    def __repr__(self) -> str:
        return f"<StudentProfiles user={self.user_id} score={self.credit_score}>"

class ModuleProgress(db.Model):
    __tablename__ = "module_progress"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True, nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey("modules.id"), index=True, nullable=False)
    current_pos = db.Column(db.Integer, default=1)      # siguiente actividad (1-based)
    score_total = db.Column(db.Integer, default=0)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

class ActivityState(db.Model):
    __tablename__ = "activity_state"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True, nullable=False)
    activity_id = db.Column(db.Integer, db.ForeignKey("activities.id"), index=True, nullable=False)
    status = db.Column(db.String(20), default="unstarted")  # unstarted|started|done
    score = db.Column(db.Integer, default=0)
    attempts = db.Column(db.Integer, default=0)
    last_submission_json = db.Column(db.Text)               # JSON serializado
    completed_at = db.Column(db.DateTime)

class Modules(db.Model):
    __tablename__ = "modules"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    summary = db.Column(db.Text)
    is_published = db.Column(db.Boolean, default=False)
    level = db.Column(db.Integer)
    xp_reward = db.Column(db.Integer)


    # 👇 one-to-many: a module has many activities
    activities = db.relationship(
        "Activities",
        back_populates="module",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

class Activities(db.Model):
    __tablename__ = "activities"
    id = db.Column(db.Integer, primary_key=True)

    # important: FK must be present and non-nullable for this relation
    module_id = db.Column(
        db.Integer,
        db.ForeignKey("modules.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    position = db.Column(db.Integer)
    title = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    max_points = db.Column(db.Integer)
    is_published = db.Column(db.Boolean)
    content_json = db.Column(db.Text)

    # new game fields (if you added them in a migration)
    attempt_limit = db.Column(db.Integer)   # nullable OK (will fallback to global default)
    default_xp    = db.Column(db.Integer)   # nullable OK

    # 👇 the other side of the relation; MUST exist to match back_populates above
    module = db.relationship("Modules", back_populates="activities")

# —— Global game knobs teachers can tune (single row id=1) ——
class GameSettings(db.Model):
    __tablename__ = "game_settings"
    id = db.Column(db.Integer, primary_key=True)
    xp_base = db.Column(db.Integer, default=100)          # XP needed for level 1→2
    xp_growth = db.Column(db.Integer, default=50)         # extra XP needed per level
    max_attempts_default = db.Column(db.Integer, default=3)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# --- Asociaciones para grupos (clases)
group_students = db.Table(
    "group_students",
    db.Column("group_id", db.Integer, db.ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
    db.Column("student_id", db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    db.UniqueConstraint("group_id", "student_id", name="uq_group_student")
)

class StudentProfiles(db.Model):
    __tablename__ = "student_profiles"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    credit_score = db.Column(db.Integer, default=650)
    cash_balance = db.Column(db.Float, default=500.0)
    salary_monthly = db.Column(db.Float, default=1200.0)
    has_car = db.Column(db.Boolean, default=False)
    car_payment_monthly = db.Column(db.Float, default=0.0)

    level = db.Column(db.Integer, default=1)
    xp = db.Column(db.Integer, default=0)
    energy = db.Column(db.Integer, default=100)

    created_at = db.Column(db.DateTime, nullable=True)

# Relación 1–1 desde Users (si no la tienes ya)
Users.profile = db.relationship(
    "StudentProfiles",
    uselist=False,
    backref="user",
    cascade="all, delete-orphan"
)

# app/models.py
from datetime import datetime
from app import db
# from sqlalchemy.orm import backref  # not needed if you use backref="group" as a string

class Groups(db.Model):
    __tablename__ = "groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)

    # IMPORTANT: map the real column name in the DB
    grade_level = db.Column(db.String(20))  # ← matches schema; replaces the old "grade" column

    # Optional columns that exist in your schema (safe to include)
    section = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    teacher_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # --- relaciones útiles para el dashboard ---
    members = db.relationship(
        "GroupMembers",
        backref="group",              # use a plain string; no need to import backref()
        cascade="all, delete-orphan",
        lazy="joined",
    )

    module_assignments = db.relationship(
        "ModuleAssignments",
        backref="group",
        cascade="all, delete-orphan",
        lazy="select",
    )

    @property
    def students(self):
        """Devuelve una lista de Users (estudiantes) en el grupo."""
        return [m.user for m in self.members]

    # Backwards-compatibility: allow templates/code that still read .grade
    @property
    def grade(self):
        return self.grade_level

class GroupMembers(db.Model):
    __tablename__ = "group_members"
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id", ondelete="CASCADE"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # relación al usuario (estudiante)
    user = db.relationship("Users", backref=backref("group_memberships", lazy="select"))

# Si tienes ModuleAssignments, opcionalmente añade backrefs si faltan:
class ModuleAssignments(db.Model):
    __tablename__ = "module_assignments"
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id", ondelete="CASCADE"))
    module_id = db.Column(db.Integer, db.ForeignKey("modules.id", ondelete="CASCADE"))
    due_date = db.Column(db.DateTime)

    module = db.relationship("Modules", backref=backref("assignments", lazy="select"))














