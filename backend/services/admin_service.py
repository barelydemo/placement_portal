"""Admin oversight: portal statistics, student management, blacklisting."""

from backend.cache import NS_STATS, bump
from backend.models import (
    Application,
    ApplicationStatus,
    ApprovalStatus,
    CompanyProfile,
    DriveStatus,
    PlacementDrive,
    StudentProfile,
    User,
    UserRole,
    db,
)
from backend.services.validators import NotFoundError, ValidationError


def _count(model, *filters) -> int:
    query = db.session.query(db.func.count(model.id))
    for condition in filters:
        query = query.filter(condition)
    return query.scalar() or 0


def compute_stats() -> dict:
    """Portal-wide counts for the admin dashboard.

    Deliberately a set of COUNT queries rather than loading rows — this is the
    most-hit endpoint in the portal, which is exactly why it is cached.
    """
    applications_by_status = {
        status.value: _count(Application, Application.status == status)
        for status in ApplicationStatus
    }

    return {
        "students": {
            "total": _count(User, User.role == UserRole.STUDENT),
            "active": _count(User, User.role == UserRole.STUDENT, User.is_active.is_(True)),
            "deactivated": _count(
                User, User.role == UserRole.STUDENT, User.is_active.is_(False)
            ),
        },
        "companies": {
            "total": _count(User, User.role == UserRole.COMPANY),
            "pending": _count(
                CompanyProfile, CompanyProfile.approval_status == ApprovalStatus.PENDING
            ),
            "approved": _count(
                CompanyProfile, CompanyProfile.approval_status == ApprovalStatus.APPROVED
            ),
            "rejected": _count(
                CompanyProfile, CompanyProfile.approval_status == ApprovalStatus.REJECTED
            ),
            "deactivated": _count(
                User, User.role == UserRole.COMPANY, User.is_active.is_(False)
            ),
        },
        "drives": {
            "total": _count(PlacementDrive),
            "pending": _count(PlacementDrive, PlacementDrive.status == DriveStatus.PENDING),
            "approved": _count(PlacementDrive, PlacementDrive.status == DriveStatus.APPROVED),
            "rejected": _count(PlacementDrive, PlacementDrive.status == DriveStatus.REJECTED),
            "closed": _count(PlacementDrive, PlacementDrive.status == DriveStatus.CLOSED),
        },
        "applications": {
            "total": _count(Application),
            "by_status": applications_by_status,
            "selected": applications_by_status[ApplicationStatus.SELECTED.value],
        },
        "pending_approvals": (
            _count(CompanyProfile, CompanyProfile.approval_status == ApprovalStatus.PENDING)
            + _count(PlacementDrive, PlacementDrive.status == DriveStatus.PENDING)
        ),
    }


def serialize_student(profile: StudentProfile) -> dict:
    """Student profile plus account fields for the admin table."""
    user = profile.user
    data = profile.to_dict()
    data.update(
        {
            "name": user.name if user else None,
            "email": user.email if user else None,
            "is_active": user.is_active if user else None,
            "applications_count": _count(Application, Application.student_id == profile.id),
        }
    )
    return data


def list_students(search: str | None = None, active: str | None = None) -> list[dict]:
    """List students, searchable by name, email or branch (partial match)."""
    query = db.session.query(StudentProfile).join(User, StudentProfile.user_id == User.id)

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            db.or_(
                User.name.ilike(term),
                User.email.ilike(term),
                StudentProfile.branch.ilike(term),
            )
        )

    if active is not None and active != "":
        wanted = str(active).strip().lower() in {"1", "true", "yes"}
        query = query.filter(User.is_active.is_(wanted))

    students = query.order_by(StudentProfile.created_at.desc()).all()
    return [serialize_student(student) for student in students]


def set_student_active(student_id: int, is_active: bool | None = None) -> StudentProfile:
    """Blacklist/deactivate or reinstate a student account.

    Deactivating flips `User.is_active` to False, which blocks login (enforced in
    auth_service.authenticate) and rejects tokens already issued (role_required).
    Omitting `is_active` toggles the current value.
    """
    profile = db.session.get(StudentProfile, student_id)
    if profile is None:
        raise NotFoundError(f"No student found with id {student_id}.")

    user = profile.user
    if user is None:
        raise NotFoundError("This student has no linked user account.")
    if user.role is not UserRole.STUDENT:
        raise ValidationError("That account is not a student.")

    user.is_active = (not user.is_active) if is_active is None else bool(is_active)
    db.session.commit()
    bump(NS_STATS)
    return profile
