"""Daily deadline/interview reminders for students.

Chosen logic (documented per Phase 6 Task A):

For every **active** student, one digest covering
  1. Approved drives whose deadline falls inside the next REMINDER_WINDOW_DAYS
     that the student **is eligible for** and has **not already applied to**, and
  2. Any **interview scheduled** within the same window.

Students with nothing in either bucket are skipped — no empty emails. The
eligibility test is `evaluate_eligibility()`, the same function used by the
browse filter and by apply-time enforcement, so a reminder can never point a
student at a drive they would be refused for.
"""

from datetime import datetime, timedelta

from backend.config import Config
from backend.models import (
    Application,
    ApplicationStatus,
    DriveStatus,
    PlacementDrive,
    StudentProfile,
    User,
    UserRole,
    db,
)
from backend.services.drive_service import evaluate_eligibility
from backend.services.notifications import send_notification
from backend.services.timeutils import now as local_now


def _now() -> datetime:
    """Server-local naive 'now' — deadlines and interview slots use this frame."""
    return local_now()


def _format_when(value: datetime) -> str:
    return value.strftime("%d %b %Y, %H:%M")


def build_reminder(profile: StudentProfile, window_end: datetime) -> dict | None:
    """Work out what this student should be reminded about, or None."""
    now = _now()

    applied_ids = {
        row[0]
        for row in db.session.query(Application.drive_id).filter_by(student_id=profile.id).all()
    }

    closing_soon = []
    candidates = (
        db.session.query(PlacementDrive)
        .filter(PlacementDrive.status == DriveStatus.APPROVED)
        .filter(PlacementDrive.application_deadline >= now)
        .filter(PlacementDrive.application_deadline <= window_end)
        .order_by(PlacementDrive.application_deadline.asc())
        .all()
    )
    for drive in candidates:
        if drive.id in applied_ids:
            continue
        eligible, _reasons = evaluate_eligibility(drive, profile)
        if eligible:
            closing_soon.append(drive)

    interviews = (
        db.session.query(Application)
        .filter(Application.student_id == profile.id)
        .filter(Application.interview_datetime.isnot(None))
        .filter(Application.interview_datetime >= now)
        .filter(Application.interview_datetime <= window_end)
        .filter(Application.status != ApplicationStatus.REJECTED)
        .order_by(Application.interview_datetime.asc())
        .all()
    )

    if not closing_soon and not interviews:
        return None

    return {
        "student_id": profile.id,
        "email": profile.user.email,
        "name": profile.user.name,
        "closing_soon": closing_soon,
        "interviews": interviews,
    }


def render_reminder_html(reminder: dict) -> str:
    parts = [
        f"<p>Hi {reminder['name']},</p>",
        "<p>Here is what needs your attention on the placement portal:</p>",
    ]

    if reminder["closing_soon"]:
        parts.append("<h3>Applications closing soon</h3><ul>")
        for drive in reminder["closing_soon"]:
            company = drive.company.company_name if drive.company else "A company"
            parts.append(
                f"<li><strong>{drive.job_title}</strong> at {company} — "
                f"closes {_format_when(drive.application_deadline)}. "
                "You are eligible but have not applied yet.</li>"
            )
        parts.append("</ul>")

    if reminder["interviews"]:
        parts.append("<h3>Upcoming interviews</h3><ul>")
        for application in reminder["interviews"]:
            drive = application.drive
            company = drive.company.company_name if drive and drive.company else "A company"
            title = drive.job_title if drive else "a drive"
            parts.append(
                f"<li><strong>{title}</strong> at {company} — "
                f"{_format_when(application.interview_datetime)} "
                f"(status: {application.status.value})</li>"
            )
        parts.append("</ul>")

    parts.append("<p>— Institute Placement Cell</p>")
    return "".join(parts)


def send_daily_reminders() -> dict:
    """Build and deliver reminders for every active student. Returns a summary."""
    window_days = Config.REMINDER_WINDOW_DAYS
    window_end = _now() + timedelta(days=window_days)

    profiles = (
        db.session.query(StudentProfile)
        .join(User, StudentProfile.user_id == User.id)
        .filter(User.role == UserRole.STUDENT)
        .filter(User.is_active.is_(True))  # blacklisted students are not chased
        .all()
    )

    sent, skipped, failed = 0, 0, 0
    details = []
    for profile in profiles:
        reminder = build_reminder(profile, window_end)
        if reminder is None:
            skipped += 1
            continue

        subject = "Placement portal: deadlines and interviews coming up"
        result = send_notification(
            reminder["email"], subject, render_reminder_html(reminder), category="reminder"
        )
        if result.get("delivered"):
            sent += 1
        else:
            failed += 1
        details.append(
            {
                "student_id": reminder["student_id"],
                "email": reminder["email"],
                "drives_closing": len(reminder["closing_soon"]),
                "interviews": len(reminder["interviews"]),
                "delivered": bool(result.get("delivered")),
            }
        )

    return {
        "job": "daily_reminders",
        "window_days": window_days,
        "students_considered": len(profiles),
        "reminders_sent": sent,
        "students_skipped": skipped,
        "failed": failed,
        "details": details,
    }
