import os
from datetime import timedelta


class Config:
    """Environment-driven config with sensible development defaults."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.environ.get("JWT_MINUTES", 30)))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.environ.get("JWT_REFRESH_DAYS", 30)))

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///dearbaby.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # The shared secret that gates the privileged signup door.
    ADMIN_INVITE_CODE = os.environ.get("ADMIN_INVITE_CODE", "dev-invite-code")

    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    ADMIN_INVITE_CODE = "test-invite"
