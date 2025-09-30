from datetime import datetime
from typing import Optional
from flask_login import UserMixin
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

class Modules(db.Model):
    __tablename__ = "modules"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    lang = db.Column(db.String(4), nullable=False, default=LOCALE_ES)
    is_published = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Activities(db.Model):
    __tablename__ = "activities"
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    type = db.Column(db.String(24), nullable=False, default="scenario")
    max_points = db.Column(db.Integer, nullable=False, default=100)
    config_json = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Attempts(db.Model):
    __tablename__ = "attempts"
    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey("activities.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    answers_json = db.Column(db.JSON, nullable=False)
    score = db.Column(db.Numeric(5,2), nullable=False, default=0.0)
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime, nullable=True)

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
