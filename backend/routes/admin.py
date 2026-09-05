"""Admin API — company oversight: list, approve, reject, deactivate.

`<company_id>` is the CompanyProfile id returned as `id` by GET /api/admin/companies.
"""

from flask import Blueprint, current_app, jsonify, request

from backend.cache import NS_STATS, get_or_set, make_key
from backend.models import UserRole
from backend.services.admin_service import (
    compute_stats,
    list_students,
    serialize_student,
    set_student_active,
)
from backend.services.company_service import (
    list_companies,
    serialize_company,
    set_active,
    set_approval,
)
from backend.services.drive_service import (
    list_admin_drives,
    serialize_drive,
    set_drive_approval,
)
from backend.services.security import role_required

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


# --- Dashboard statistics (cached) ------------------------------------------


@admin_bp.get("/stats")
@role_required(UserRole.ADMIN)
def stats():
    """Portal-wide counts for the admin dashboard.

    Served from Redis for CACHE_STATS_TTL seconds. Writes elsewhere bump the
    stats namespace, so a relevant change refreshes this immediately rather than
    waiting for the TTL. The X-Cache header reports HIT or MISS.
    """
    ttl = current_app.config["CACHE_STATS_TTL"]
    key = make_key(NS_STATS, {"endpoint": "admin_stats"})
    data, was_hit = get_or_set(key, ttl, compute_stats)

    response = jsonify({"stats": data, "cached": was_hit, "ttl_seconds": ttl})
    response.headers["X-Cache"] = "HIT" if was_hit else "MISS"
    return response


# --- Background job triggers (demo convenience) -----------------------------


@admin_bp.post("/reports/monthly/trigger")
@role_required(UserRole.ADMIN)
def trigger_monthly_report():
    """Queue the monthly activity report now instead of waiting for the 1st."""
    from backend.tasks.jobs import send_monthly_report

    async_result = send_monthly_report.delay()
    return (
        jsonify(
            {
                "message": "Monthly report queued.",
                "task_id": async_result.id,
                "status_url": f"/api/tasks/{async_result.id}/status",
            }
        ),
        202,
    )


@admin_bp.post("/reminders/trigger")
@role_required(UserRole.ADMIN)
def trigger_daily_reminders():
    """Queue the daily reminder sweep now (normally runs on Celery beat)."""
    from backend.tasks.jobs import send_daily_reminders

    async_result = send_daily_reminders.delay()
    return (
        jsonify(
            {
                "message": "Daily reminders queued.",
                "task_id": async_result.id,
                "status_url": f"/api/tasks/{async_result.id}/status",
            }
        ),
        202,
    )


# --- Students ---------------------------------------------------------------


@admin_bp.get("/students")
@role_required(UserRole.ADMIN)
def students():
    """List/search students by name, email or branch."""
    students_list = list_students(
        search=request.args.get("search"), active=request.args.get("active")
    )
    return jsonify({"students": students_list, "count": len(students_list)})


@admin_bp.put("/students/<int:student_id>/deactivate")
@role_required(UserRole.ADMIN)
def deactivate_student(student_id: int):
    """Blacklist/reinstate a student. Body may set {"is_active": bool}; omitted = toggle."""
    payload = request.get_json(silent=True) or {}
    profile = set_student_active(student_id, payload.get("is_active"))
    state = "reinstated" if profile.user.is_active else "deactivated"
    return jsonify(
        {
            "message": f"{profile.user.name} {state}.",
            "student": serialize_student(profile),
        }
    )


@admin_bp.get("/companies")
@role_required(UserRole.ADMIN)
def companies():
    """List companies, optionally filtered by status, name/email search, or active flag."""
    companies_list = list_companies(
        status=request.args.get("status"),
        search=request.args.get("search"),
        active=request.args.get("active"),
    )
    return jsonify({"companies": companies_list, "count": len(companies_list)})


@admin_bp.put("/companies/<int:company_id>/approve")
@role_required(UserRole.ADMIN)
def approve_company(company_id: int):
    profile = set_approval(company_id, approved=True)
    return jsonify(
        {
            "message": f"{profile.company_name} approved.",
            "company": serialize_company(profile),
        }
    )


@admin_bp.put("/companies/<int:company_id>/reject")
@role_required(UserRole.ADMIN)
def reject_company(company_id: int):
    payload = request.get_json(silent=True) or {}
    profile = set_approval(company_id, approved=False, reason=payload.get("reason"))
    return jsonify(
        {
            "message": f"{profile.company_name} rejected.",
            "company": serialize_company(profile),
        }
    )


@admin_bp.put("/companies/<int:company_id>/deactivate")
@role_required(UserRole.ADMIN)
def deactivate_company(company_id: int):
    """Blacklist/reinstate a company. Body may set {"is_active": bool}; omitted = toggle."""
    payload = request.get_json(silent=True) or {}
    profile = set_active(company_id, payload.get("is_active"))
    state = "reinstated" if profile.user.is_active else "deactivated"
    return jsonify(
        {
            "message": f"{profile.company_name} {state}.",
            "company": serialize_company(profile),
        }
    )


# --- Placement drive approval queue -----------------------------------------


@admin_bp.get("/drives")
@role_required(UserRole.ADMIN)
def drives():
    """List all drives, optionally filtered by status or title/company search."""
    drives_list = list_admin_drives(
        status=request.args.get("status"), search=request.args.get("search")
    )
    return jsonify({"drives": drives_list, "count": len(drives_list)})


@admin_bp.put("/drives/<int:drive_id>/approve")
@role_required(UserRole.ADMIN)
def approve_drive(drive_id: int):
    drive = set_drive_approval(drive_id, approved=True)
    return jsonify(
        {"message": f"'{drive.job_title}' approved.", "drive": serialize_drive(drive)}
    )


@admin_bp.put("/drives/<int:drive_id>/reject")
@role_required(UserRole.ADMIN)
def reject_drive(drive_id: int):
    payload = request.get_json(silent=True) or {}
    drive = set_drive_approval(drive_id, approved=False, reason=payload.get("reason"))
    return jsonify(
        {"message": f"'{drive.job_title}' rejected.", "drive": serialize_drive(drive)}
    )
