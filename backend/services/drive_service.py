"""Placement drive lifecycle: creation, approval, browsing, eligibility.

Deadlines are stored as naive UTC datetimes. A date-only input ("2026-09-30")
is treated as the end of that day, so the deadline day itself is inclusive.
"""

from datetime import datetime, time, timezone

from backend.cache import NS_DRIVES, NS_STATS, bump
from backend.models import (
    ApprovalStatus,
    CompanyProfile,
    DriveStatus,
    PlacementDrive,
    StudentProfile,
    User,
    UserRole,
    db,
)
from backend.services.timeutils import now as local_now
from backend.services.validators import (
    ForbiddenError,
    NotFoundError,
    ValidationError,
    require_text,
    validate_cgpa,
)

MAX_REJECTION_REASON = 500


def _now() -> datetime:
    """Server-local naive 'now' — the frame deadlines are stored in."""
    return local_now()


def parse_deadline(payload: dict, field: str = "application_deadline") -> datetime:
    raw = (payload.get(field) or "").strip()
    if not raw:
        raise ValidationError("Application deadline is required.", field)

    text = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        raise ValidationError(
            "Deadline must be a date (YYYY-MM-DD) or ISO datetime.", field
        ) from None

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)

    # A bare date means "any time that day" — make the whole day count.
    if len(raw) == 10 and parsed.time() == time(0, 0):
        parsed = datetime.combine(parsed.date(), time(23, 59, 59))

    if parsed <= _now():
        raise ValidationError("Application deadline must be in the future.", field)
    return parsed


def _parse_branches(payload: dict) -> str | None:
    raw = payload.get("eligible_branches")
    if raw is None or raw == "":
        return None
    items = raw if isinstance(raw, list) else str(raw).split(",")
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    if not cleaned:
        return None
    joined = ",".join(cleaned)
    if len(joined) > 500:
        raise ValidationError("Too many eligible branches listed.", "eligible_branches")
    return joined


def _parse_years(payload: dict) -> str | None:
    raw = payload.get("eligible_years")
    if raw is None or raw == "":
        return None
    items = raw if isinstance(raw, list) else str(raw).split(",")
    years = []
    for item in items:
        value = str(item).strip()
        if not value:
            continue
        try:
            year = int(value)
        except ValueError:
            raise ValidationError(
                f"'{value}' is not a valid graduation year.", "eligible_years"
            ) from None
        if not 1990 <= year <= 2100:
            raise ValidationError(
                "Eligible years must be between 1990 and 2100.", "eligible_years"
            )
        years.append(str(year))
    return ",".join(years) if years else None


# --- Eligibility -------------------------------------------------------------


def evaluate_eligibility(
    drive: PlacementDrive, profile: StudentProfile | None
) -> tuple[bool, list[str]]:
    """Check a student against a drive's criteria.

    Returns (is_eligible, reasons_if_not). Phase 4 reuses this to enforce
    eligibility at application time, so the browse filter and the enforcement
    can never drift apart.
    """
    reasons: list[str] = []
    if profile is None:
        return False, ["No student profile on record."]

    branches = drive.branch_list
    if branches:
        student_branch = (profile.branch or "").strip().lower()
        if not student_branch:
            reasons.append("Your branch is not set on your profile.")
        elif student_branch not in [branch.lower() for branch in branches]:
            reasons.append(f"Open to {', '.join(branches)} only.")

    if drive.min_cgpa is not None:
        if profile.cgpa is None:
            reasons.append("Your CGPA is not set on your profile.")
        elif profile.cgpa < drive.min_cgpa:
            reasons.append(f"Requires CGPA {drive.min_cgpa} (yours is {profile.cgpa}).")

    years = drive.year_list
    if years:
        if profile.graduation_year is None:
            reasons.append("Your graduation year is not set on your profile.")
        elif profile.graduation_year not in years:
            reasons.append(f"Open to {', '.join(str(y) for y in years)} batches only.")

    return (not reasons), reasons


def serialize_drive(
    drive: PlacementDrive,
    profile: StudentProfile | None = None,
    applied_ids: set[int] | None = None,
) -> dict:
    """Drive payload; includes eligibility/applied state when a student is supplied."""
    data = drive.to_dict()
    if profile is not None:
        eligible, reasons = evaluate_eligibility(drive, profile)
        data["is_eligible"] = eligible
        data["ineligibility_reasons"] = reasons
        data["has_applied"] = drive.id in applied_ids if applied_ids is not None else False
    return data


# --- Company ----------------------------------------------------------------


def _company_profile(user: User) -> CompanyProfile:
    profile = user.company_profile
    if profile is None:
        raise NotFoundError("No company profile is linked to this account.")
    return profile


def create_drive(user: User, payload: dict) -> PlacementDrive:
    """Create a drive. Only an approved company may do this."""
    profile = _company_profile(user)
    if profile.approval_status is not ApprovalStatus.APPROVED:
        raise ForbiddenError(
            "Your company must be approved by the admin before you can post drives. "
            f"Current status: {profile.approval_status.value}."
        )

    drive = PlacementDrive(
        company_id=profile.id,
        job_title=require_text(payload, "job_title", "Job title", max_length=200),
        job_description=require_text(
            payload, "job_description", "Job description", max_length=5000
        ),
        eligible_branches=_parse_branches(payload),
        min_cgpa=validate_cgpa(payload, "min_cgpa"),
        eligible_years=_parse_years(payload),
        application_deadline=parse_deadline(payload),
        status=DriveStatus.PENDING,  # admin approves before students see it
    )
    db.session.add(drive)
    db.session.commit()
    bump(NS_STATS)
    bump(NS_DRIVES)
    return drive


def list_company_drives(user: User, status: str | None = None) -> list[dict]:
    profile = _company_profile(user)
    query = db.session.query(PlacementDrive).filter_by(company_id=profile.id)
    if status:
        query = query.filter(PlacementDrive.status == _parse_status(status))
    drives = query.order_by(PlacementDrive.created_at.desc()).all()
    return [serialize_drive(drive) for drive in drives]


def close_drive(user: User, drive_id: int) -> PlacementDrive:
    """Close a drive so it stops appearing to students.

    Companies may close their own drives; the admin may close any.
    """
    drive = _get_drive(drive_id)
    if user.role is UserRole.COMPANY:
        profile = _company_profile(user)
        if drive.company_id != profile.id:
            raise ForbiddenError("You can only close your own drives.")
    elif user.role is not UserRole.ADMIN:
        raise ForbiddenError("Only the owning company or an admin can close a drive.")

    drive.status = DriveStatus.CLOSED
    db.session.commit()
    bump(NS_STATS)
    bump(NS_DRIVES)  # a closed drive must disappear from student listings at once
    return drive


# --- Admin ------------------------------------------------------------------


def _parse_status(status: str) -> DriveStatus:
    normalized = status.strip().lower()
    valid = {item.value.lower(): item for item in DriveStatus}
    if normalized not in valid:
        raise ValidationError(
            "Status filter must be one of: pending, approved, rejected, closed.", "status"
        )
    return valid[normalized]


def list_admin_drives(status: str | None = None, search: str | None = None) -> list[dict]:
    query = db.session.query(PlacementDrive).join(
        CompanyProfile, PlacementDrive.company_id == CompanyProfile.id
    )
    if status:
        query = query.filter(PlacementDrive.status == _parse_status(status))
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            db.or_(
                PlacementDrive.job_title.ilike(term),
                CompanyProfile.company_name.ilike(term),
            )
        )
    drives = query.order_by(PlacementDrive.created_at.desc()).all()
    return [serialize_drive(drive) for drive in drives]


def _get_drive(drive_id: int) -> PlacementDrive:
    drive = db.session.get(PlacementDrive, drive_id)
    if drive is None:
        raise NotFoundError(f"No drive found with id {drive_id}.")
    return drive


def set_drive_approval(
    drive_id: int, approved: bool, reason: str | None = None
) -> PlacementDrive:
    drive = _get_drive(drive_id)
    if approved:
        drive.status = DriveStatus.APPROVED
        drive.rejection_reason = None
    else:
        cleaned = (reason or "").strip()
        if len(cleaned) > MAX_REJECTION_REASON:
            raise ValidationError(
                f"Rejection reason must be at most {MAX_REJECTION_REASON} characters.",
                "reason",
            )
        drive.status = DriveStatus.REJECTED
        drive.rejection_reason = cleaned or None
    db.session.commit()
    bump(NS_STATS)
    bump(NS_DRIVES)  # approval changes what students can see
    return drive


# --- Student ----------------------------------------------------------------


def list_student_drives(
    user: User,
    search: str | None = None,
    branch: str | None = None,
    cgpa: str | None = None,
    eligible_only: str | None = None,
) -> list[dict]:
    """Approved drives that are still open, with optional filters.

    Rejected, Pending and Closed drives are never returned, nor are drives whose
    deadline has passed.
    """
    profile = user.student_profile

    query = (
        db.session.query(PlacementDrive)
        .join(CompanyProfile, PlacementDrive.company_id == CompanyProfile.id)
        .filter(PlacementDrive.status == DriveStatus.APPROVED)
        .filter(PlacementDrive.application_deadline >= _now())
    )

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            db.or_(
                PlacementDrive.job_title.ilike(term),
                PlacementDrive.job_description.ilike(term),
                CompanyProfile.company_name.ilike(term),
            )
        )

    if branch:
        term = f"%{branch.strip()}%"
        # A drive with no branch restriction is open to everyone, so it matches too.
        query = query.filter(
            db.or_(
                PlacementDrive.eligible_branches.is_(None),
                PlacementDrive.eligible_branches == "",
                PlacementDrive.eligible_branches.ilike(term),
            )
        )

    if cgpa not in (None, ""):
        try:
            value = float(cgpa)
        except (TypeError, ValueError):
            raise ValidationError("CGPA filter must be a number.", "cgpa") from None
        query = query.filter(
            db.or_(PlacementDrive.min_cgpa.is_(None), PlacementDrive.min_cgpa <= value)
        )

    # Imported here to avoid a circular import (application_service uses this module).
    from backend.services.application_service import applied_drive_ids

    drives = query.order_by(PlacementDrive.application_deadline.asc()).all()
    applied = applied_drive_ids(profile)
    results = [serialize_drive(drive, profile, applied) for drive in drives]

    if str(eligible_only).strip().lower() in {"1", "true", "yes"}:
        results = [drive for drive in results if drive["is_eligible"]]
    return results


# --- Shared detail ----------------------------------------------------------


def get_drive_detail(user: User, drive_id: int) -> dict:
    """Drive detail, scoped by role.

    Admin sees any drive; a company sees its own drives plus approved ones;
    a student sees approved drives only (past deadline included, so links to a
    drive they already looked at keep working).
    """
    drive = _get_drive(drive_id)

    if user.role is UserRole.ADMIN:
        return serialize_drive(drive)

    if user.role is UserRole.COMPANY:
        profile = _company_profile(user)
        if drive.company_id == profile.id or drive.status is DriveStatus.APPROVED:
            return serialize_drive(drive)
        raise ForbiddenError("You can only view your own drives.")

    if drive.status is not DriveStatus.APPROVED:
        raise ForbiddenError("This drive is not open for viewing.")

    from backend.services.application_service import applied_drive_ids

    return serialize_drive(drive, user.student_profile, applied_drive_ids(user.student_profile))
