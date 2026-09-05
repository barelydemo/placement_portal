"""Shared drive detail endpoint — available to any authenticated role.

Visibility is scoped per role inside `get_drive_detail`.
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import current_user, jwt_required

from backend.services.drive_service import get_drive_detail

drives_bp = Blueprint("drives", __name__, url_prefix="/api/drives")


@drives_bp.get("/<int:drive_id>")
@jwt_required()
def drive_detail(drive_id: int):
    return jsonify({"drive": get_drive_detail(current_user, drive_id)})
