"""Registration and login business logic."""

from backend.cache import NS_STATS, bump
from backend.models import (
    ApprovalStatus,
    CompanyProfile,
    StudentProfile,
    User,
    UserRole,
    db,
)
from backend.services.validators import (
    AuthenticationError,
    ValidationError,
    require_text,
    validate_cgpa,
    validate_email,
    validate_graduation_year,
    validate_password,
    validate_website,
)

# Only these two roles may ever self-register. Admin is seeded, never signed up.
SELF_REGISTERABLE_ROLES = {"student", "company"}


def _parse_role(payload: dict) -> UserRole:
    role = (payload.get("role") or "").strip().lower()
    if not role:
        raise ValidationError("Role is required (student or company).", "role")
    if role == "admin":
        raise ValidationError(
            "Admin accounts cannot be registered. The institute admin is pre-seeded.",
            "role",
        )
    if role not in SELF_REGISTERABLE_ROLES:
        raise ValidationError("Role must be either 'student' or 'company'.", "role")
    return UserRole(role)


def register_user(payload: dict) -> User:
    """Create a student or company account together with its profile."""
    role = _parse_role(payload)
    email = validate_email(payload)
    password = validate_password(payload)

    if db.session.query(User).filter_by(email=email).first():
        raise ValidationError("An account with this email already exists.", "email")

    if role is UserRole.STUDENT:
        name = require_text(payload, "name", "Full name", max_length=120)
        profile = StudentProfile(
            branch=(payload.get("branch") or "").strip() or None,
            cgpa=validate_cgpa(payload),
            graduation_year=validate_graduation_year(payload),
            phone=(payload.get("phone") or "").strip() or None,
        )
    else:
        # A company's display name is the company name itself.
        name = require_text(payload, "company_name", "Company name", max_length=120)
        profile = CompanyProfile(
            company_name=name,
            hr_contact=(payload.get("hr_contact") or "").strip() or None,
            website=validate_website(payload),
            approval_status=ApprovalStatus.PENDING,  # admin approves in Phase 2
        )

    user = User(name=name, email=email, role=role, is_active=True)
    user.set_password(password)

    if role is UserRole.STUDENT:
        user.student_profile = profile
    else:
        user.company_profile = profile

    db.session.add(user)
    db.session.commit()
    bump(NS_STATS)  # student/company totals changed
    return user


def authenticate(payload: dict) -> User:
    """Validate credentials for any role, including the seeded admin."""
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    if not email or not password:
        raise ValidationError("Email and password are required.")

    user = db.session.query(User).filter_by(email=email).first()
    # Same message for unknown email and wrong password — do not leak which
    # emails are registered.
    if user is None or not user.check_password(password):
        raise AuthenticationError()
    if not user.is_active:
        raise AuthenticationError("This account has been deactivated. Contact the admin.")
    return user


def serialize_user(user: User) -> dict:
    """User payload returned by /login and /me, including the role profile."""
    data = user.to_dict()
    profile = user.profile
    data["profile"] = profile.to_dict() if profile else None
    return data
