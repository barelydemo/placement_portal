"""Authentication plumbing: JWT manager, role-based access control, errors."""

from functools import wraps

from flask import jsonify
from flask_jwt_extended import JWTManager, current_user, verify_jwt_in_request

from backend.cache.token_blocklist import is_revoked
from backend.models import User, UserRole

jwt = JWTManager()


def init_jwt(app) -> None:
    """Attach the JWT manager and all of its callbacks to the Flask app."""
    jwt.init_app(app)


@jwt.user_identity_loader
def _user_identity(user: User) -> str:
    # The JWT `sub` claim must be a string.
    return str(user.id)


@jwt.user_lookup_loader
def _user_lookup(_jwt_header, jwt_data) -> User | None:
    """Load the User for every protected request.

    Deliberately hits the DB instead of trusting the token's role claim, so that
    deactivating a user takes effect immediately rather than at token expiry.
    """
    identity = jwt_data.get("sub")
    if identity is None:
        return None
    return User.query.filter_by(id=int(identity)).first()


@jwt.token_in_blocklist_loader
def _check_revoked(_jwt_header, jwt_data) -> bool:
    return is_revoked(jwt_data["jti"])


# --- JSON error responses (never HTML error pages for API clients) ---


@jwt.unauthorized_loader
def _missing_token(reason: str):
    return jsonify({"error": "Authentication required.", "detail": reason}), 401


@jwt.invalid_token_loader
def _invalid_token(reason: str):
    return jsonify({"error": "Invalid token.", "detail": reason}), 401


@jwt.expired_token_loader
def _expired_token(_jwt_header, _jwt_data):
    return jsonify({"error": "Session expired. Please log in again."}), 401


@jwt.revoked_token_loader
def _revoked_token(_jwt_header, _jwt_data):
    return jsonify({"error": "This session has been logged out."}), 401


@jwt.user_lookup_error_loader
def _user_not_found(_jwt_header, _jwt_data):
    return jsonify({"error": "User account no longer exists."}), 401


def role_required(*roles: UserRole):
    """Restrict a route to the given roles.

    Returns 401 when unauthenticated, 403 when authenticated as the wrong role.
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user = current_user
            if user is None:
                return jsonify({"error": "Authentication required."}), 401
            if not user.is_active:
                return jsonify({"error": "This account has been deactivated."}), 403
            if user.role not in roles:
                allowed = ", ".join(role.value for role in roles)
                return (
                    jsonify(
                        {
                            "error": "You do not have permission to access this resource.",
                            "required_role": allowed,
                            "your_role": user.role.value,
                        }
                    ),
                    403,
                )
            return fn(*args, **kwargs)

        return wrapper

    return decorator
