"""CSV export of a student's applications (runs inside a Celery task)."""

import csv
from datetime import datetime, timezone

from backend.config import Config
from backend.models import Application, StudentProfile, db
from backend.services.notifications import send_notification

COLUMNS = [
    "Application ID",
    "Student ID",
    "Student Name",
    "Company Name",
    "Drive Title",
    "Application Status",
    "Applied Date",
    "Application Deadline",
    "Interview Date",
    "Last Updated",
]


def _fmt(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d %H:%M") if value else ""


def build_rows(profile: StudentProfile) -> list[list[str]]:
    applications = (
        db.session.query(Application)
        .filter_by(student_id=profile.id)
        .order_by(Application.applied_at.asc())
        .all()
    )

    rows = []
    for application in applications:
        drive = application.drive
        company = drive.company if drive else None
        rows.append(
            [
                application.id,
                profile.id,
                profile.user.name if profile.user else "",
                company.company_name if company else "",
                drive.job_title if drive else "",
                application.status.value,
                _fmt(application.applied_at),
                _fmt(drive.application_deadline) if drive else "",
                _fmt(application.interview_datetime),
                _fmt(application.updated_at),
            ]
        )
    return rows


def export_applications(student_profile_id: int, task_id: str) -> dict:
    """Write the student's applications to a CSV file and notify them.

    The file is named after the task id so the download endpoint can find it,
    and the returned payload records the owner so downloads can be authorised.
    """
    profile = db.session.get(StudentProfile, student_profile_id)
    if profile is None:
        raise ValueError(f"No student profile with id {student_profile_id}")

    Config.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"applications_{student_profile_id}_{task_id}.csv"
    file_path = Config.EXPORT_DIR / filename

    rows = build_rows(profile)
    with file_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(COLUMNS)
        writer.writerows(rows)

    # "Alert once done", per PROJECT_CONTEXT section 6.
    send_notification(
        profile.user.email if profile.user else Config.ADMIN_EMAIL,
        "Your applications export is ready",
        (
            f"<p>Hi {profile.user.name if profile.user else 'there'},</p>"
            f"<p>Your export of {len(rows)} application(s) is ready to download "
            "from the My Applications page.</p>"
            "<p>— Institute Placement Cell</p>"
        ),
        category="export_ready",
    )

    return {
        "job": "export_applications",
        "student_id": student_profile_id,
        "task_id": task_id,
        "filename": filename,
        "row_count": len(rows),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
