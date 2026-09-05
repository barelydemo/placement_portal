"""Input validation for the API layer.

The Vue forms use HTML5 validation for fast feedback, but that is trivially
bypassed, so every rule is enforced again here on the server.
"""

import re

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")
MIN_PASSWORD_LENGTH = 8


class ValidationError(Exception):
    """Raised when submitted data fails a rule. Message is safe to show users."""

    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.message = message
        self.field = field


class ConflictError(Exception):
    """Raised when an action clashes with existing state — HTTP 409.

    Used for duplicate applications: the request is well-formed, it just cannot
    happen twice.
    """

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ForbiddenError(Exception):
    """Raised when an authenticated user may not perform this action — HTTP 403."""

    def __init__(self, message: str = "You are not allowed to perform this action."):
        super().__init__(message)
        self.message = message


class NotFoundError(Exception):
    """Raised when a requested record does not exist — surfaced as HTTP 404."""

    def __init__(self, message: str = "Resource not found."):
        super().__init__(message)
        self.message = message


class AuthenticationError(Exception):
    """Raised when credentials are rejected — surfaced as HTTP 401, not 400."""

    def __init__(self, message: str = "Invalid email or password."):
        super().__init__(message)
        self.message = message


def require_text(payload: dict, field: str, label: str, max_length: int = 255) -> str:
    value = (payload.get(field) or "").strip()
    if not value:
        raise ValidationError(f"{label} is required.", field)
    if len(value) > max_length:
        raise ValidationError(f"{label} must be at most {max_length} characters.", field)
    return value


def validate_email(payload: dict, field: str = "email") -> str:
    email = (payload.get(field) or "").strip().lower()
    if not email:
        raise ValidationError("Email is required.", field)
    if not EMAIL_RE.match(email):
        raise ValidationError("Enter a valid email address.", field)
    return email


def validate_password(payload: dict, field: str = "password") -> str:
    password = payload.get(field) or ""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters.", field
        )
    return password


def validate_cgpa(payload: dict, field: str = "cgpa") -> float | None:
    raw = payload.get(field)
    if raw is None or raw == "":
        return None
    try:
        cgpa = float(raw)
    except (TypeError, ValueError):
        raise ValidationError("CGPA must be a number.", field) from None
    if not 0 <= cgpa <= 10:
        raise ValidationError("CGPA must be between 0 and 10.", field)
    return cgpa


def validate_graduation_year(payload: dict, field: str = "graduation_year") -> int | None:
    raw = payload.get(field)
    if raw is None or raw == "":
        return None
    try:
        year = int(raw)
    except (TypeError, ValueError):
        raise ValidationError("Graduation year must be a number.", field) from None
    if not 1990 <= year <= 2100:
        raise ValidationError("Graduation year must be between 1990 and 2100.", field)
    return year


def validate_website(payload: dict, field: str = "website") -> str | None:
    website = (payload.get(field) or "").strip()
    if not website:
        return None
    if not re.match(r"^https?://", website, re.IGNORECASE):
        website = f"https://{website}"
    if len(website) > 255:
        raise ValidationError("Website URL is too long.", field)
    return website
