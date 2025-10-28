import os
from dotenv import load_dotenv
load_dotenv()

def _db_url():
    uri = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5433/appdb")
    if uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
    return uri

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-change")
    SQLALCHEMY_DATABASE_URI = _db_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    WTF_CSRF_TIME_LIMIT = None
