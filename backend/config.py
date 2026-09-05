"""Central configuration for the Placement Portal Application.

Values come from the environment (loaded from a .env file at the project root)
with development-friendly defaults so the skeleton runs out of the box.
"""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# <project_root>/backend/config.py -> <project_root>
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def _resolve_db_path(raw_path: str) -> Path:
    """Resolve the DB path against the project root when it is relative.

    This keeps `flask run`, `seed.py` and the Celery worker pointed at the same
    SQLite file no matter which directory they were launched from.
    """
    path = Path(raw_path)
    return path if path.is_absolute() else BASE_DIR / path


class Config:
    # --- Flask ---
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")

    # Never let a browser hold on to a stale copy of the Vue app in development.
    SEND_FILE_MAX_AGE_DEFAULT = 0

    # --- Paths ---
    BASE_DIR = BASE_DIR
    TEMPLATE_DIR = BASE_DIR / "frontend" / "templates"
    STATIC_DIR = BASE_DIR / "frontend" / "static"

    # --- Database (SQLite only, created programmatically) ---
    DATABASE_PATH = _resolve_db_path(os.getenv("DATABASE_PATH", "placement.db"))
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH.as_posix()}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Auth ---
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv("JWT_ACCESS_TOKEN_HOURS", "8")))

    # --- Redis / Celery ---
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    CACHE_DEFAULT_TIMEOUT = int(os.getenv("CACHE_DEFAULT_TIMEOUT", "300"))
    # Per-endpoint cache lifetimes (seconds). Writes also invalidate explicitly.
    CACHE_STATS_TTL = int(os.getenv("CACHE_STATS_TTL", "60"))
    CACHE_DRIVES_TTL = int(os.getenv("CACHE_DRIVES_TTL", "60"))

    # --- Notifications ---
    # "log" (default) renders messages to a file + logger without credentials.
    # "smtp" sends real email; "chat" posts to a Google Chat webhook.
    NOTIFICATION_BACKEND = os.getenv("NOTIFICATION_BACKEND", "log").strip().lower()
    NOTIFICATION_LOG_FILE = BASE_DIR / "var" / "notifications.log"
    MAIL_FROM = os.getenv("MAIL_FROM", "placement-cell@ppa.local")
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes"}
    GOOGLE_CHAT_WEBHOOK_URL = os.getenv("GOOGLE_CHAT_WEBHOOK_URL", "")

    # --- Background jobs ---
    REMINDER_WINDOW_DAYS = int(os.getenv("REMINDER_WINDOW_DAYS", "2"))
    REMINDER_HOUR = int(os.getenv("REMINDER_HOUR", "9"))
    REMINDER_MINUTE = int(os.getenv("REMINDER_MINUTE", "0"))
    MONTHLY_REPORT_HOUR = int(os.getenv("MONTHLY_REPORT_HOUR", "6"))
    MONTHLY_REPORT_MINUTE = int(os.getenv("MONTHLY_REPORT_MINUTE", "0"))
    EXPORT_DIR = BASE_DIR / "var" / "exports"

    # --- Uploads (resumes) ---
    RESUME_DIR = BASE_DIR / "var" / "resumes"
    ALLOWED_RESUME_EXTENSIONS = {".pdf", ".doc", ".docx"}
    MAX_RESUME_MB = int(os.getenv("MAX_RESUME_MB", "5"))
    # Flask rejects anything larger outright (returns 413).
    MAX_CONTENT_LENGTH = MAX_RESUME_MB * 1024 * 1024

    # --- Seeded admin (single superuser, no registration route ever) ---
    ADMIN_NAME = os.getenv("ADMIN_NAME", "Institute Placement Cell")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@ppa.local")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@123")
