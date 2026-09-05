"""Entry-point routes.

`/` is the ONLY server-rendered page: a Jinja2 shell that boots the Vue app.
All dynamic UI is rendered by Vue on the client, never by Jinja2.
"""

from flask import Blueprint, current_app, jsonify, render_template
from sqlalchemy import text

from backend.cache import ping as redis_ping
from backend.models import db

main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def index():
    """Serve the single Jinja2 entry point that mounts the Vue application."""
    return render_template("index.html", app_name="Placement Portal Application")


@main_bp.get("/api/health")
def health():
    """Report skeleton health so Phase 0 can be verified end to end."""
    try:
        db.session.execute(text("SELECT 1"))
        database_ok = True
    except Exception:  # noqa: BLE001 - report any failure as "not ready"
        database_ok = False

    return jsonify(
        {
            "status": "ok",
            "app": "Placement Portal Application",
            "phase": 7,
            "database": "connected" if database_ok else "unavailable",
            "database_file": str(current_app.config["DATABASE_PATH"]),
            "redis": "connected" if redis_ping() else "unavailable",
        }
    )
