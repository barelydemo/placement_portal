"""Monthly activity report for the admin.

Runs on the 1st and covers the **previous** calendar month: drives conducted,
students who applied, students selected.
"""

from datetime import datetime, timedelta, timezone

from backend.config import Config
from backend.models import (
    Application,
    ApplicationStatus,
    CompanyProfile,
    PlacementDrive,
    User,
    UserRole,
    db,
)
from backend.services.notifications import send_notification


def previous_month_range(reference: datetime | None = None) -> tuple[datetime, datetime, str]:
    """Return (start, end, label) for the calendar month before `reference`."""
    now = reference or datetime.now(timezone.utc).replace(tzinfo=None)
    first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # Step back one day from the 1st to land in the previous month.
    last_of_prev = first_of_this_month - timedelta(days=1)
    start = last_of_prev.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, first_of_this_month, start.strftime("%B %Y")


def build_monthly_report(reference: datetime | None = None) -> dict:
    """Aggregate the previous month's placement activity."""
    start, end, label = previous_month_range(reference)

    drives = (
        db.session.query(PlacementDrive)
        .filter(PlacementDrive.created_at >= start, PlacementDrive.created_at < end)
        .all()
    )
    applications = (
        db.session.query(Application)
        .filter(Application.applied_at >= start, Application.applied_at < end)
        .all()
    )

    students_applied = {application.student_id for application in applications}
    selected = [
        application
        for application in applications
        if application.status is ApplicationStatus.SELECTED
    ]
    students_selected = {application.student_id for application in selected}

    new_companies = (
        db.session.query(db.func.count(CompanyProfile.id))
        .filter(CompanyProfile.created_at >= start, CompanyProfile.created_at < end)
        .scalar()
        or 0
    )
    new_students = (
        db.session.query(db.func.count(User.id))
        .filter(
            User.role == UserRole.STUDENT, User.created_at >= start, User.created_at < end
        )
        .scalar()
        or 0
    )

    return {
        "period_label": label,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "drives_conducted": len(drives),
        "applications_received": len(applications),
        "students_applied": len(students_applied),
        "students_selected": len(students_selected),
        "selections": len(selected),
        "new_companies": new_companies,
        "new_students": new_students,
        "drive_breakdown": [
            {
                "job_title": drive.job_title,
                "company": drive.company.company_name if drive.company else None,
                "status": drive.status.value,
                "applicants": drive.applicant_count,
            }
            for drive in drives
        ],
    }


def render_report_html(report: dict) -> str:
    rows = "".join(
        f"<tr><td>{item['job_title']}</td><td>{item['company'] or '—'}</td>"
        f"<td>{item['status']}</td><td align='right'>{item['applicants']}</td></tr>"
        for item in report["drive_breakdown"]
    ) or "<tr><td colspan='4'>No drives were created in this period.</td></tr>"

    return f"""
    <html><body style="font-family: Arial, Helvetica, sans-serif; color:#212529;">
      <h2>Placement activity report — {report['period_label']}</h2>
      <p>Summary of campus placement activity for the period.</p>
      <table cellpadding="8" cellspacing="0" border="0" style="border-collapse:collapse;">
        <tr style="background:#f8f9fa;"><td><strong>Drives conducted</strong></td>
            <td align="right"><strong>{report['drives_conducted']}</strong></td></tr>
        <tr><td>Applications received</td><td align="right">{report['applications_received']}</td></tr>
        <tr style="background:#f8f9fa;"><td>Students who applied</td>
            <td align="right">{report['students_applied']}</td></tr>
        <tr><td>Students selected</td><td align="right">{report['students_selected']}</td></tr>
        <tr style="background:#f8f9fa;"><td>New companies registered</td>
            <td align="right">{report['new_companies']}</td></tr>
        <tr><td>New students registered</td><td align="right">{report['new_students']}</td></tr>
      </table>

      <h3>Drives in this period</h3>
      <table cellpadding="6" cellspacing="0" border="1"
             style="border-collapse:collapse; border-color:#dee2e6;">
        <tr style="background:#f8f9fa;">
          <th align="left">Job title</th><th align="left">Company</th>
          <th align="left">Status</th><th align="right">Applicants</th>
        </tr>
        {rows}
      </table>

      <p style="color:#6c757d; font-size:12px;">
        Generated automatically by the Placement Portal Application.
      </p>
    </body></html>
    """


def send_monthly_report(reference: datetime | None = None) -> dict:
    """Build the report and send it to the admin."""
    report = build_monthly_report(reference)
    admin = (
        db.session.query(User)
        .filter(User.role == UserRole.ADMIN)
        .order_by(User.id.asc())
        .first()
    )
    recipient = admin.email if admin else Config.ADMIN_EMAIL

    result = send_notification(
        recipient,
        f"Monthly placement report — {report['period_label']}",
        render_report_html(report),
        category="monthly_report",
    )

    return {
        "job": "monthly_report",
        "recipient": recipient,
        "delivered": bool(result.get("delivered")),
        "report": report,
    }
