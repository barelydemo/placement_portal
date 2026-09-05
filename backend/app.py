"""Flask application factory for the Placement Portal Application."""

from pathlib import Path

from flask import Flask, jsonify, url_for

from backend.config import Config
from backend.models import db
from backend.routes import (
    admin_bp,
    auth_bp,
    company_bp,
    dashboard_bp,
    drives_bp,
    main_bp,
    student_bp,
    tasks_bp,
)
from backend.services.security import init_jwt
from backend.services.validators import (
    AuthenticationError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)


def create_app(config_object: type[Config] = Config) -> Flask:
    """Build and configure the Flask app.

    Templates and static files live under `frontend/`, outside this package, so
    both folders are pointed at explicitly.
    """
    app = Flask(
        __name__,
        template_folder=str(config_object.TEMPLATE_DIR),
        static_folder=str(config_object.STATIC_DIR),
    )
    app.config.from_object(config_object)

    db.init_app(app)
    init_jwt(app)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(company_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(drives_bp)
    app.register_blueprint(tasks_bp)

    @app.context_processor
    def _asset_helper():
        """Expose `asset()` to templates: a static URL stamped with the file's mtime.

        Editing a JS/CSS file changes its URL, so the browser can never serve a
        stale copy of the Vue app after a change.
        """

        def asset(filename: str) -> str:
            file_path = Path(app.static_folder) / filename
            version = int(file_path.stat().st_mtime) if file_path.exists() else 0
            return url_for("static", filename=filename, v=version)

        return {"asset": asset}

    # Fallback so a validation failure anywhere returns JSON, never an HTML page.
    @app.errorhandler(ValidationError)
    def _handle_validation_error(error: ValidationError):
        return jsonify({"error": error.message, "field": error.field}), 400

    @app.errorhandler(AuthenticationError)
    def _handle_auth_error(error: AuthenticationError):
        return jsonify({"error": error.message}), 401

    @app.errorhandler(ConflictError)
    def _handle_conflict(error: ConflictError):
        return jsonify({"error": error.message}), 409

    @app.errorhandler(ForbiddenError)
    def _handle_forbidden(error: ForbiddenError):
        return jsonify({"error": error.message}), 403

    @app.errorhandler(NotFoundError)
    def _handle_not_found(error: NotFoundError):
        return jsonify({"error": error.message}), 404

    @app.errorhandler(404)
    def _handle_404(_error):
        return jsonify({"error": "Resource not found."}), 404

    @app.errorhandler(405)
    def _handle_405(_error):
        return jsonify({"error": "That HTTP method is not allowed on this endpoint."}), 405

    @app.errorhandler(413)
    def _handle_too_large(_error):
        limit = app.config["MAX_RESUME_MB"]
        return jsonify({"error": f"File is too large. Maximum size is {limit} MB."}), 413

    @app.errorhandler(Exception)
    def _handle_unexpected(error):
        """Last resort: log the detail, return JSON without leaking internals."""
        from werkzeug.exceptions import HTTPException

        if isinstance(error, HTTPException):
            return (
                jsonify({"error": error.description or error.name}),
                error.code or 500,
            )
        app.logger.exception("Unhandled error: %s", error)
        return jsonify({"error": "An unexpected server error occurred."}), 500

    return app


if __name__ == "__main__":  # pragma: no cover - run with: python -m backend.app
    create_app().run(debug=True)
