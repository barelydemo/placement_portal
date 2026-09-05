"""Authentication API — register, login, me, logout.

One login endpoint serves all three roles; the response carries the role so the
Vue app knows where to redirect. There is deliberately no admin registration.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, current_user, get_jwt, jwt_required

from backend.cache.token_blocklist import revoke
from backend.services.auth_service import authenticate, register_user, serialize_user
from backend.services.validators import AuthenticationError, ValidationError

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.errorhandler(ValidationError)
def _handle_validation_error(error: ValidationError):
    return jsonify({"error": error.message, "field": error.field}), 400


@auth_bp.errorhandler(AuthenticationError)
def _handle_authentication_error(error: AuthenticationError):
    return jsonify({"error": error.message}), 401


@auth_bp.post("/register")
def register():
    """Self-registration for students and companies only."""
    payload = request.get_json(silent=True) or {}
    user = register_user(payload)
    return (
        jsonify(
            {
                "message": f"{user.role.value.capitalize()} registered successfully. Please log in.",
                "user": serialize_user(user),
            }
        ),
        201,
    )


@auth_bp.post("/login")
def login():
    """Log in any role, including the seeded admin."""
    payload = request.get_json(silent=True) or {}
    user = authenticate(payload)
    token = create_access_token(identity=user, additional_claims={"role": user.role.value})
    return jsonify(
        {
            "message": "Login successful.",
            "access_token": token,
            "user": serialize_user(user),
        }
    )


@auth_bp.get("/me")
@jwt_required()
def me():
    """Return the currently authenticated user and role."""
    return jsonify({"user": serialize_user(current_user)})


@auth_bp.post("/logout")
@jwt_required()
def logout():
    """Revoke the current token so it cannot be reused."""
    claims = get_jwt()
    ttl = max(claims["exp"] - claims["iat"], 1)
    revoked = revoke(claims["jti"], ttl)
    return jsonify(
        {
            "message": "Logged out successfully.",
            # False means Redis was unreachable; the client still drops the token.
            "token_revoked": revoked,
        }
    )
