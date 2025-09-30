import os
from dotenv import load_dotenv
load_dotenv()
class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-change")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///econquest.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_SECURE = False   # True en prod con HTTPS
    REMEMBER_COOKIE_SECURE = False  # True en prod
    WTF_CSRF_TIME_LIMIT = None
