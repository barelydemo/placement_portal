"""SQLAlchemy setup and model registry.

`db` lives here (rather than in app.py) so models and the app factory never
import each other circularly. Every model module must be imported below so that
`db.create_all()` sees it and creates the table programmatically.
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from backend.models.user import User, UserRole  # noqa: E402,F401
from backend.models.company_profile import ApprovalStatus, CompanyProfile  # noqa: E402,F401
from backend.models.student_profile import StudentProfile  # noqa: E402,F401
from backend.models.placement_drive import DriveStatus, PlacementDrive  # noqa: E402,F401
from backend.models.application import Application, ApplicationStatus  # noqa: E402,F401

__all__ = [
    "db",
    "User",
    "UserRole",
    "CompanyProfile",
    "ApprovalStatus",
    "StudentProfile",
    "PlacementDrive",
    "DriveStatus",
    "Application",
    "ApplicationStatus",
]
