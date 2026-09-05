"""The three background jobs required by PROJECT_CONTEXT section 6.

Each task is a thin wrapper: the logic lives in the service layer so it can be
called and tested directly, without a broker.
"""

import logging

from backend.services.export_service import export_applications
from backend.services.reminder_service import send_daily_reminders as _send_reminders
from backend.services.reporting_service import send_monthly_report as _send_report
from backend.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="ppa.send_daily_reminders")
def send_daily_reminders():
    """Scheduled daily: nudge students about deadlines and interviews."""
    summary = _send_reminders()
    logger.info(
        "Daily reminders: %s sent, %s skipped, %s failed",
        summary["reminders_sent"],
        summary["students_skipped"],
        summary["failed"],
    )
    return summary


@celery_app.task(name="ppa.send_monthly_report")
def send_monthly_report():
    """Scheduled on the 1st: email the admin last month's activity."""
    summary = _send_report()
    logger.info(
        "Monthly report for %s sent to %s (delivered=%s)",
        summary["report"]["period_label"],
        summary["recipient"],
        summary["delivered"],
    )
    return summary


@celery_app.task(name="ppa.export_applications", bind=True)
def export_applications_task(self, student_profile_id: int):
    """User-triggered: build a CSV of one student's applications."""
    result = export_applications(student_profile_id, self.request.id)
    logger.info(
        "Export ready for student %s: %s (%s rows)",
        student_profile_id,
        result["filename"],
        result["row_count"],
    )
    return result
