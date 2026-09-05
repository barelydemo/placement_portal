"""Role-protected placeholder dashboards.

Phase 1 only proves that role-based access control works; the real dashboard
data (stats, drives, applications) is filled in from Phase 2 onwards.
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import current_user

from backend.services.auth_service import serialize_user
from backend.services.security import role_required
from backend.models import UserRole

dashboard_bp = Blueprint("dashboards", __name__, url_prefix="/api")


@dashboard_bp.get("/admin/dashboard")
@role_required(UserRole.ADMIN)
def admin_dashboard():
    return jsonify(
        {
            "area": "admin",
            "message": f"Welcome, {current_user.name}. Admin area (placeholder).",
            "user": serialize_user(current_user),
        }
    )


@dashboard_bp.get("/company/dashboard")
@role_required(UserRole.COMPANY)
def company_dashboard():
    profile = current_user.company_profile
    return jsonify(
        {
            "area": "company",
            "message": f"Welcome, {current_user.name}. Company area (placeholder).",
            "approval_status": profile.approval_status.value if profile else None,
            "user": serialize_user(current_user),
        }
    )


@dashboard_bp.get("/student/dashboard")
@role_required(UserRole.STUDENT)
def student_dashboard():
    return jsonify(
        {
            "area": "student",
            "message": f"Welcome, {current_user.name}. Student area (placeholder).",
            "user": serialize_user(current_user),
        }
    )
