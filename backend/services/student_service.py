"""Student self-service profile management.

The academic fields here drive eligibility, so they are validated with the same
rules used at registration.
"""

from backend.cache import NS_DRIVES, bump
from backend.models import StudentProfile, User, db
from backend.services.validators import (
    NotFoundError,
    require_text,
    validate_cgpa,
    validate_graduation_year,
)


def get_profile(user: User) -> StudentProfile:
    profile = user.student_profile
    if profile is None:
        raise NotFoundError("No student profile is linked to this account.")
    return profile


def serialize_student_profile(profile: StudentProfile) -> dict:
    data = profile.to_dict()
    user = profile.user
    data.update(
        {
            "name": user.name if user else None,
            "email": user.email if user else None,
            "is_active": user.is_active if user else None,
        }
    )
    return data


def update_profile(user: User, payload: dict) -> StudentProfile:
    """Update the student's own details.

    Changing branch/CGPA/year changes which drives they qualify for, so the
    cached drive listings are invalidated.
    """
    profile = get_profile(user)

    name = require_text(payload, "name", "Full name", max_length=120)
    cgpa = validate_cgpa(payload)
    graduation_year = validate_graduation_year(payload)

    user.name = name
    profile.branch = (payload.get("branch") or "").strip() or None
    profile.cgpa = cgpa
    profile.graduation_year = graduation_year
    profile.phone = (payload.get("phone") or "").strip() or None

    db.session.commit()
    bump(NS_DRIVES)  # eligibility flags in cached listings are now stale
    return profile
