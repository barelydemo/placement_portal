"""HTTP layer — blueprints registered by the app factory."""

from backend.routes.admin import admin_bp
from backend.routes.auth import auth_bp
from backend.routes.company import company_bp
from backend.routes.dashboards import dashboard_bp
from backend.routes.drives import drives_bp
from backend.routes.main import main_bp
from backend.routes.student import student_bp
from backend.routes.tasks import tasks_bp

__all__ = [
    "main_bp",
    "auth_bp",
    "dashboard_bp",
    "company_bp",
    "admin_bp",
    "student_bp",
    "drives_bp",
    "tasks_bp",
]
