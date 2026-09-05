"""Applications: applying, tracking, and company-side status management."""

from datetime import datetime, timezone

from backend.cache import NS_DRIVES, NS_STATS, bump
from backend.models import (
    Application,
    ApplicationStatus,
    CompanyProfile,
    DriveStatus,
    PlacementDrive,
    StudentProfile,
    User,
    UserRole,
    db,
)
from backend.services.drive_service import evaluate_eligibility
from backend.services.validators import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _student_profile(user: User) -> StudentProfile:
    profile = user.student_profile
    if profile is None:
        raise NotFoundError("No student profile is linked to this account.")
    return profile


def _company_profile(user: User) -> CompanyProfile:
    profile = user.company_profile
    if profile is None:
        raise NotFoundError("No company profile is linked to this account.")
    return profile


def serialize_application(
    application: Application, include_drive: bool = False, include_student: bool = False
) -> dict:
    """Application payload, optionally joined with drive or student details."""
    data = application.to_dict()

    if include_drive:
        drive = application.drive
        data["drive"] = (
            {
                "id": drive.id,
                "job_title": drive.job_title,
                "company_name": drive.company.company_name if drive.company else None,
                "application_deadline": (
                    drive.application_deadline.isoformat()
                    if drive.application_deadline
                    else None
                ),
                "status": drive.status.value,
                "is_past_deadline": drive.is_past_deadline,
            }
            if drive
            else None
        )

    if include_student:
        student = application.student
        user = student.user if student else None
        data["student"] = (
            {
                "id": student.id,
                "user_id": student.user_id,
                "name": user.name if user else None,
                "email": user.email if user else None,
                "branch": student.branch,
                "cgpa": student.cgpa,
                "graduation_year": student.graduation_year,
                "phone": student.phone,
            }
            if student
            else None
        )

    return data


# --- Student ----------------------------------------------------------------


def apply_to_drive(user: User, payload: dict) -> Application:
    """Apply to a drive, enforcing every gate the portal requires.

    Order of checks is deliberate: the student learns the most useful reason
    first (drive unavailable -> deadline -> already applied -> ineligible).
    """
    profile = _student_profile(user)

    raw_id = payload.get("drive_id")
    if raw_id in (None, ""):
        raise ValidationError("A drive_id is required.", "drive_id")
    try:
        drive_id = int(raw_id)
    except (TypeError, ValueError):
        raise ValidationError("drive_id must be a number.", "drive_id") from None

    drive = db.session.get(PlacementDrive, drive_id)
    if drive is None:
        raise NotFoundError(f"No drive found with id {drive_id}.")

    if drive.status is not DriveStatus.APPROVED:
        raise ForbiddenError("This drive is not open for applications.")

    if drive.is_past_deadline:
        raise ForbiddenError("The application deadline for this drive has passed.")

    existing = (
        db.session.query(Application)
        .filter_by(student_id=profile.id, drive_id=drive.id)
        .first()
    )
    if existing:
        raise ConflictError("You have already applied to this drive.")

    eligible, reasons = evaluate_eligibility(drive, profile)
    if not eligible:
        raise ForbiddenError("You are not eligible for this drive. " + " ".join(reasons))

    application = Application(
        student_id=profile.id, drive_id=drive.id, status=ApplicationStatus.APPLIED
    )
    db.session.add(application)
    db.session.commit()
    bump(NS_STATS)
    bump(NS_DRIVES)  # has_applied flipped for this student's drive listing
    return application


def list_student_applications(user: User, status: str | None = None) -> list[dict]:
    """The student's applications — current and past (placement history)."""
    profile = _student_profile(user)
    query = db.session.query(Application).filter_by(student_id=profile.id)
    if status:
        query = query.filter(Application.status == _parse_status(status))
    applications = query.order_by(Application.applied_at.desc()).all()
    return [serialize_application(item, include_drive=True) for item in applications]


# --- Company ----------------------------------------------------------------


def _parse_status(status: str) -> ApplicationStatus:
    normalized = (status or "").strip().lower()
    valid = {item.value.lower(): item for item in ApplicationStatus}
    if normalized not in valid:
        raise ValidationError(
            "Status must be one of: Applied, Shortlisted, Selected, Rejected.", "status"
        )
    return valid[normalized]


def _drive_for_company(user: User, drive_id: int) -> PlacementDrive:
    """Fetch a drive, ensuring a company user owns it. Admins may view any."""
    drive = db.session.get(PlacementDrive, drive_id)
    if drive is None:
        raise NotFoundError(f"No drive found with id {drive_id}.")
    if user.role is UserRole.ADMIN:
        return drive
    profile = _company_profile(user)
    if drive.company_id != profile.id:
        raise ForbiddenError("You can only view applicants for your own drives.")
    return drive


def list_drive_applications(
    user: User, drive_id: int, status: str | None = None
) -> list[dict]:
    """Applicants for one drive, with student details for screening."""
    drive = _drive_for_company(user, drive_id)
    query = db.session.query(Application).filter_by(drive_id=drive.id)
    if status:
        query = query.filter(Application.status == _parse_status(status))
    applications = query.order_by(Application.applied_at.asc()).all()
    return [serialize_application(item, include_student=True) for item in applications]


def _parse_interview_datetime(payload: dict) -> datetime | None:
    raw = payload.get("interview_datetime")
    if raw in (None, ""):
        return None
    text = str(raw).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        raise ValidationError(
            "Interview datetime must be an ISO datetime (YYYY-MM-DDTHH:MM).",
            "interview_datetime",
        ) from None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def update_application_status(user: User, application_id: int, payload: dict) -> Application:
    """Company moves an applicant through the pipeline, optionally scheduling an interview."""
    application = db.session.get(Application, application_id)
    if application is None:
        raise NotFoundError(f"No application found with id {application_id}.")

    # Ownership is decided by the drive the application belongs to.
    _drive_for_company(user, application.drive_id)

    if "status" not in payload or payload.get("status") in (None, ""):
        raise ValidationError("A status is required.", "status")

    application.status = _parse_status(payload.get("status"))

    # Only touch the interview slot when the caller actually sent the field,
    # so a plain status change never wipes an existing booking.
    if "interview_datetime" in payload:
        application.interview_datetime = _parse_interview_datetime(payload)

    application.updated_at = _now()
    db.session.commit()
    bump(NS_STATS)  # application status counts changed
    return application


# --- Helpers used by drive listings ----------------------------------------


def applied_drive_ids(profile: StudentProfile | None) -> set[int]:
    """Drive ids this student has already applied to (one query, not N)."""
    if profile is None:
        return set()
    rows = db.session.query(Application.drive_id).filter_by(student_id=profile.id).all()
    return {row[0] for row in rows}
