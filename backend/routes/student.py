"""Student API — browsing approved placement drives."""

from flask import Blueprint, current_app, jsonify, request, send_file
from flask_jwt_extended import current_user

from backend.cache import NS_DRIVES, get_or_set, make_key
from backend.models import UserRole
from backend.services.application_service import (
    apply_to_drive,
    list_student_applications,
    serialize_application,
)
from backend.services.drive_service import list_student_drives
from backend.services.resume_service import own_resume, save_resume
from backend.services.security import role_required
from backend.services.student_service import (
    get_profile,
    serialize_student_profile,
    update_profile,
)
from backend.services.validators import ForbiddenError, NotFoundError

student_bp = Blueprint("student", __name__, url_prefix="/api/student")


# --- Profile + resume -------------------------------------------------------


@student_bp.get("/profile")
@role_required(UserRole.STUDENT)
def student_profile():
    """The student's own profile, including resume status."""
    return jsonify({"student": serialize_student_profile(get_profile(current_user))})


@student_bp.put("/profile")
@role_required(UserRole.STUDENT)
def edit_student_profile():
    """Update own academic details (these determine drive eligibility)."""
    payload = request.get_json(silent=True) or {}
    profile = update_profile(current_user, payload)
    return jsonify(
        {
            "message": "Profile updated successfully.",
            "student": serialize_student_profile(profile),
        }
    )


@student_bp.post("/resume")
@role_required(UserRole.STUDENT)
def upload_resume():
    """Upload/replace the student's resume (PDF or Word, max MAX_RESUME_MB)."""
    profile = save_resume(current_user, request.files.get("resume"))
    return jsonify(
        {
            "message": "Resume uploaded successfully.",
            "student": serialize_student_profile(profile),
        }
    )


@student_bp.get("/resume/download")
@role_required(UserRole.STUDENT)
def download_own_resume():
    """Download the student's own resume."""
    path, download_name = own_resume(current_user)
    return send_file(path, as_attachment=True, download_name=download_name)


@student_bp.get("/drives")
@role_required(UserRole.STUDENT)
def browse_drives():
    """Approved, still-open drives with search and eligibility filters.

    Query params: search, branch, cgpa, eligible_only.

    Cached in Redis per student AND per filter combination: the payload carries
    `is_eligible` / `has_applied`, which are specific to the caller, so the
    student's profile id is part of the cache key. Applying to a drive or any
    drive write bumps the namespace, refreshing this immediately.
    """
    filters = {
        "search": request.args.get("search"),
        "branch": request.args.get("branch"),
        "cgpa": request.args.get("cgpa"),
        "eligible_only": request.args.get("eligible_only"),
    }
    profile = current_user.student_profile
    ttl = current_app.config["CACHE_DRIVES_TTL"]
    key = make_key(
        NS_DRIVES,
        {
            "endpoint": "student_drives",
            "student_id": profile.id if profile else None,
            "filters": filters,
        },
    )

    drives, was_hit = get_or_set(
        key, ttl, lambda: list_student_drives(current_user, **filters)
    )

    response = jsonify({"drives": drives, "count": len(drives), "cached": was_hit})
    response.headers["X-Cache"] = "HIT" if was_hit else "MISS"
    return response


@student_bp.post("/applications")
@role_required(UserRole.STUDENT)
def apply():
    """Apply to a drive.

    Rejected with 409 if already applied, 403 if ineligible / closed / past
    deadline, 404 if the drive does not exist.
    """
    payload = request.get_json(silent=True) or {}
    application = apply_to_drive(current_user, payload)
    return (
        jsonify(
            {
                "message": "Application submitted successfully.",
                "application": serialize_application(application, include_drive=True),
            }
        ),
        201,
    )


@student_bp.get("/applications")
@role_required(UserRole.STUDENT)
def my_applications():
    """The student's applications — doubles as placement history."""
    applications = list_student_applications(current_user, status=request.args.get("status"))
    return jsonify({"applications": applications, "count": len(applications)})


# --- Async CSV export -------------------------------------------------------


@student_bp.post("/applications/export")
@role_required(UserRole.STUDENT)
def export_applications():
    """Queue a CSV export and return immediately with a task id.

    This never waits for the CSV to be built — the client polls
    /api/tasks/<task_id>/status and then downloads.
    """
    from backend.tasks.jobs import export_applications_task

    profile = current_user.student_profile
    if profile is None:
        raise NotFoundError("No student profile is linked to this account.")

    async_result = export_applications_task.delay(profile.id)
    return (
        jsonify(
            {
                "message": "Export started. You will be notified when it is ready.",
                "task_id": async_result.id,
                "status_url": f"/api/tasks/{async_result.id}/status",
                "download_url": f"/api/student/applications/export/{async_result.id}/download",
            }
        ),
        202,
    )


@student_bp.get("/applications/export/<task_id>/download")
@role_required(UserRole.STUDENT)
def download_export(task_id: str):
    """Download a finished export — only the student who requested it."""
    from celery.result import AsyncResult

    from backend.tasks.celery_app import celery_app

    profile = current_user.student_profile
    if profile is None:
        raise NotFoundError("No student profile is linked to this account.")

    result = AsyncResult(task_id, app=celery_app)
    if not result.successful():
        raise NotFoundError("That export is not ready yet.")

    payload = result.result or {}
    # A task id is not a secret — confirm this export belongs to the caller.
    if payload.get("student_id") != profile.id:
        raise ForbiddenError("That export belongs to another student.")

    file_path = current_app.config["EXPORT_DIR"] / payload["filename"]
    if not file_path.exists():
        raise NotFoundError("The export file is no longer available. Please export again.")

    return send_file(
        file_path,
        mimetype="text/csv",
        as_attachment=True,
        download_name="my_applications.csv",
    )
