"""Company self-service API — a company managing its own profile."""

from flask import Blueprint, Response, jsonify, request, send_file
from flask_jwt_extended import current_user

from backend.models import UserRole
from backend.services.company_service import (
    get_profile_for_user,
    serialize_company,
    update_profile,
)
from backend.services.application_service import (
    list_drive_applications,
    serialize_application,
    update_application_status,
)
from backend.services.drive_service import (
    close_drive,
    create_drive,
    list_company_drives,
    serialize_drive,
)
from backend.services.offer_letter_service import build_offer_letter, get_selected_application
from backend.services.resume_service import resume_file
from backend.services.security import role_required
from backend.services.validators import ForbiddenError, NotFoundError

company_bp = Blueprint("company", __name__, url_prefix="/api/company")


@company_bp.get("/profile")
@role_required(UserRole.COMPANY)
def get_profile():
    """Return the logged-in company's own profile and approval status."""
    profile = get_profile_for_user(current_user)
    return jsonify({"company": serialize_company(profile)})


@company_bp.put("/profile")
@role_required(UserRole.COMPANY)
def edit_profile():
    """Update the company's own details.

    Editing sends an Approved or Rejected company back to Pending for re-review.
    """
    payload = request.get_json(silent=True) or {}
    profile, status_was_reset = update_profile(current_user, payload)
    message = "Profile updated successfully."
    if status_was_reset:
        message += " Your profile is pending admin re-approval."
    return jsonify(
        {
            "message": message,
            "status_reset": status_was_reset,
            "company": serialize_company(profile),
        }
    )


# --- Placement drives -------------------------------------------------------


@company_bp.post("/drives")
@role_required(UserRole.COMPANY)
def create_company_drive():
    """Post a new drive — rejected with 403 unless the company is approved."""
    payload = request.get_json(silent=True) or {}
    drive = create_drive(current_user, payload)
    return (
        jsonify(
            {
                "message": "Drive submitted for admin approval.",
                "drive": serialize_drive(drive),
            }
        ),
        201,
    )


@company_bp.get("/drives")
@role_required(UserRole.COMPANY)
def list_own_drives():
    """List this company's drives with status and applicant counts."""
    drives = list_company_drives(current_user, status=request.args.get("status"))
    return jsonify({"drives": drives, "count": len(drives)})


@company_bp.put("/drives/<int:drive_id>/close")
@role_required(UserRole.COMPANY, UserRole.ADMIN)
def close_company_drive(drive_id: int):
    """Close a drive so students no longer see it."""
    drive = close_drive(current_user, drive_id)
    return jsonify(
        {"message": f"'{drive.job_title}' closed.", "drive": serialize_drive(drive)}
    )


# --- Applicants -------------------------------------------------------------


@company_bp.get("/drives/<int:drive_id>/applications")
@role_required(UserRole.COMPANY, UserRole.ADMIN)
def drive_applications(drive_id: int):
    """Applicants for one of this company's drives (admins may view any)."""
    applications = list_drive_applications(
        current_user, drive_id, status=request.args.get("status")
    )
    return jsonify({"applications": applications, "count": len(applications)})


@company_bp.put("/applications/<int:application_id>/status")
@role_required(UserRole.COMPANY, UserRole.ADMIN)
def set_application_status(application_id: int):
    """Move an applicant to Shortlisted / Selected / Rejected.

    Optionally accepts `interview_datetime`; omitting the field leaves any
    existing interview booking untouched.
    """
    payload = request.get_json(silent=True) or {}
    application = update_application_status(current_user, application_id, payload)
    return jsonify(
        {
            "message": f"Application marked {application.status.value}.",
            "application": serialize_application(application, include_student=True),
        }
    )


def _own_application(application_id: int):
    """Load an application, ensuring the caller owns the drive behind it."""
    from backend.models import Application, UserRole as Role, db

    application = db.session.get(Application, application_id)
    if application is None:
        raise NotFoundError(f"No application found with id {application_id}.")
    if current_user.role is Role.ADMIN:
        return application
    profile = current_user.company_profile
    drive = application.drive
    if profile is None or drive is None or drive.company_id != profile.id:
        raise ForbiddenError("That application belongs to another company's drive.")
    return application


@company_bp.get("/applications/<int:application_id>/resume")
@role_required(UserRole.COMPANY, UserRole.ADMIN)
def applicant_resume(application_id: int):
    """Download an applicant's resume — only for the company running the drive."""
    application = _own_application(application_id)
    student = application.student
    if student is None:
        raise NotFoundError("This application has no student profile attached.")
    path, download_name = resume_file(student)
    return send_file(path, as_attachment=True, download_name=download_name)


@company_bp.get("/applications/<int:application_id>/offer-letter")
@role_required(UserRole.COMPANY, UserRole.ADMIN)
def offer_letter(application_id: int):
    """Generate a specimen offer letter for a Selected candidate.

    Optional query params: ctc, joining_date, location. Anything omitted renders
    as a visible placeholder rather than an invented term.
    """
    _own_application(application_id)  # ownership first, then eligibility
    application = get_selected_application(application_id)

    letter = build_offer_letter(
        application,
        {
            "ctc": request.args.get("ctc"),
            "joining_date": request.args.get("joining_date"),
            "location": request.args.get("location"),
        },
    )
    return Response(
        letter["html"],
        mimetype="text/html",
        headers={"Content-Disposition": f'inline; filename="{letter["filename"]}"'},
    )
