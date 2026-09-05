"""Company profile management and admin approval workflow.

`company_id` throughout this module means `CompanyProfile.id` (the "Company ID"
of PROJECT_CONTEXT section 4), not the underlying `User.id`. Both are returned
in serialized output so the frontend never has to guess.
"""

from backend.cache import NS_DRIVES, NS_STATS, bump
from backend.models import ApprovalStatus, CompanyProfile, User, UserRole, db
from backend.services.validators import (
    NotFoundError,
    ValidationError,
    require_text,
    validate_website,
)

MAX_REJECTION_REASON = 500


def serialize_company(profile: CompanyProfile) -> dict:
    """Company profile plus the account fields the admin table needs."""
    user = profile.user
    data = profile.to_dict()
    data.update(
        {
            "email": user.email if user else None,
            "is_active": user.is_active if user else None,
            "account_name": user.name if user else None,
        }
    )
    return data


def get_profile_for_user(user: User) -> CompanyProfile:
    profile = user.company_profile
    if profile is None:
        raise NotFoundError("No company profile is linked to this account.")
    return profile


def update_profile(user: User, payload: dict) -> tuple[CompanyProfile, bool]:
    """Update the company's own profile and send it back for admin re-review.

    Any edit by an already-Approved or Rejected company resets the status to
    Pending: approved companies get re-reviewed on their new details, and
    rejected ones get to fix the problem and resubmit. Any stale rejection
    reason is cleared at the same time.

    Returns (profile, status_was_reset).
    """
    profile = get_profile_for_user(user)

    company_name = require_text(payload, "company_name", "Company name", max_length=120)
    hr_contact = require_text(payload, "hr_contact", "HR contact", max_length=120)
    website = validate_website(payload)

    profile.company_name = company_name
    profile.hr_contact = hr_contact
    profile.website = website
    # The account's display name is the company name — keep them in sync.
    user.name = company_name

    status_was_reset = profile.approval_status is not ApprovalStatus.PENDING
    if status_was_reset:
        profile.approval_status = ApprovalStatus.PENDING
        profile.rejection_reason = None

    db.session.commit()
    # Company name appears on drive listings; approval counts feed the stats.
    bump(NS_STATS)
    bump(NS_DRIVES)
    return profile, status_was_reset


def list_companies(status: str | None = None, search: str | None = None,
                   active: str | None = None) -> list[dict]:
    """List companies for the admin panel, with optional status/search filters."""
    query = db.session.query(CompanyProfile).join(User, CompanyProfile.user_id == User.id)

    if status:
        normalized = status.strip().lower()
        if normalized not in {"pending", "approved", "rejected"}:
            raise ValidationError(
                "Status filter must be one of: pending, approved, rejected.", "status"
            )
        query = query.filter(CompanyProfile.approval_status == ApprovalStatus(normalized.capitalize()))

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            db.or_(CompanyProfile.company_name.ilike(term), User.email.ilike(term))
        )

    if active is not None and active != "":
        wanted = str(active).strip().lower() in {"1", "true", "yes"}
        query = query.filter(User.is_active.is_(wanted))

    companies = query.order_by(CompanyProfile.created_at.desc()).all()
    return [serialize_company(company) for company in companies]


def _get_company(company_id: int) -> CompanyProfile:
    profile = db.session.get(CompanyProfile, company_id)
    if profile is None:
        raise NotFoundError(f"No company found with id {company_id}.")
    return profile


def set_approval(company_id: int, approved: bool, reason: str | None = None) -> CompanyProfile:
    """Approve or reject a company. Approving clears any previous reason."""
    profile = _get_company(company_id)

    if approved:
        profile.approval_status = ApprovalStatus.APPROVED
        profile.rejection_reason = None
    else:
        cleaned = (reason or "").strip()
        if len(cleaned) > MAX_REJECTION_REASON:
            raise ValidationError(
                f"Rejection reason must be at most {MAX_REJECTION_REASON} characters.",
                "reason",
            )
        profile.approval_status = ApprovalStatus.REJECTED
        profile.rejection_reason = cleaned or None

    db.session.commit()
    bump(NS_STATS)
    return profile


def set_active(company_id: int, is_active: bool | None = None) -> CompanyProfile:
    """Blacklist/deactivate or reinstate a company account.

    Deactivating flips `User.is_active` to False, which blocks login outright
    (enforced in auth_service.authenticate) and rejects any token still in use
    (enforced in role_required). Omitting `is_active` toggles the current value.
    """
    profile = _get_company(company_id)
    user = profile.user
    if user is None:
        raise NotFoundError("This company has no linked user account.")
    if user.role is not UserRole.COMPANY:
        raise ValidationError("That account is not a company.")

    user.is_active = (not user.is_active) if is_active is None else bool(is_active)
    db.session.commit()
    bump(NS_STATS)
    return profile
