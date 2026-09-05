"""Student resume upload, storage and retrieval.

Safety notes:
* The stored filename is generated from the student id — never from the upload —
  so a crafted name like ``../../app.py`` cannot escape the resume directory.
* The extension is checked against a whitelist, and Flask's MAX_CONTENT_LENGTH
  rejects oversized bodies before they reach this code.
"""

from datetime import datetime
from pathlib import Path

from werkzeug.utils import secure_filename

from backend.config import Config
from backend.models import StudentProfile, User, db
from backend.services.validators import NotFoundError, ValidationError


def _profile_for(user: User) -> StudentProfile:
    profile = user.student_profile
    if profile is None:
        raise NotFoundError("No student profile is linked to this account.")
    return profile


def save_resume(user: User, file_storage) -> StudentProfile:
    """Validate and store an uploaded resume, replacing any previous one."""
    if file_storage is None or not file_storage.filename:
        raise ValidationError("Please choose a file to upload.", "resume")

    original_name = secure_filename(file_storage.filename)
    extension = Path(original_name).suffix.lower()
    if extension not in Config.ALLOWED_RESUME_EXTENSIONS:
        allowed = ", ".join(sorted(Config.ALLOWED_RESUME_EXTENSIONS))
        raise ValidationError(f"Resume must be one of: {allowed}", "resume")

    profile = _profile_for(user)
    Config.RESUME_DIR.mkdir(parents=True, exist_ok=True)

    # Server-controlled filename: the upload never decides the path.
    stored_name = f"resume_student_{profile.id}{extension}"
    destination = Config.RESUME_DIR / stored_name

    # Remove a previous resume in a different format so no orphan is left behind.
    if profile.resume_path and profile.resume_path != stored_name:
        old = Config.RESUME_DIR / profile.resume_path
        if old.exists():
            old.unlink()

    file_storage.save(destination)

    if destination.stat().st_size == 0:
        destination.unlink()
        raise ValidationError("That file is empty.", "resume")

    profile.resume_path = stored_name
    profile.resume_original_name = original_name
    profile.resume_uploaded_at = datetime.now()
    db.session.commit()
    return profile


def resume_file(profile: StudentProfile) -> tuple[Path, str]:
    """Return (path, download name) for a stored resume."""
    if not profile.resume_path:
        raise NotFoundError("No resume has been uploaded yet.")
    path = Config.RESUME_DIR / profile.resume_path
    if not path.exists():
        raise NotFoundError("The stored resume file is missing. Please upload it again.")
    return path, profile.resume_original_name or profile.resume_path


def own_resume(user: User) -> tuple[Path, str]:
    return resume_file(_profile_for(user))
