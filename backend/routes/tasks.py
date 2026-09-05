"""Task status polling for user-triggered background jobs."""

from celery.result import AsyncResult
from flask import Blueprint, jsonify
from flask_jwt_extended import current_user, jwt_required

from backend.models import UserRole
from backend.services.validators import ForbiddenError
from backend.tasks.celery_app import celery_app

tasks_bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")

# States Celery reports; PENDING also covers "unknown id" and "no worker running".
_FINISHED = {"SUCCESS", "FAILURE", "REVOKED"}


@tasks_bp.get("/<task_id>/status")
@jwt_required()
def task_status(task_id: str):
    """Report progress of a background task.

    A student may only poll their own tasks; the admin may poll any.
    """
    result = AsyncResult(task_id, app=celery_app)
    state = result.state
    payload = result.result if result.successful() else None

    if (
        payload
        and current_user.role is UserRole.STUDENT
        and payload.get("student_id") is not None
    ):
        profile = current_user.student_profile
        if profile is None or payload.get("student_id") != profile.id:
            raise ForbiddenError("That task belongs to another user.")

    body = {
        "task_id": task_id,
        "state": state,
        "ready": state in _FINISHED,
        "successful": state == "SUCCESS",
    }

    if state == "SUCCESS":
        body["result"] = payload
    elif state == "FAILURE":
        # Surface the error type only — never the raw traceback.
        body["error"] = type(result.result).__name__ if result.result else "TaskFailed"
    elif state == "PENDING":
        body["hint"] = (
            "Still queued. If this never changes, check that a Celery worker is running."
        )

    return jsonify(body)
