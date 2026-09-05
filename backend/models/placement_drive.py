"""Placement drive posted by a company and approved by the admin."""

import enum
from datetime import datetime, timezone

from backend.models import db


class DriveStatus(enum.Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    CLOSED = "Closed"


def _split_csv(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


class PlacementDrive(db.Model):
    __tablename__ = "placement_drives"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(
        db.Integer, db.ForeignKey("company_profiles.id"), nullable=False, index=True
    )
    job_title = db.Column(db.String(200), nullable=False)
    job_description = db.Column(db.Text, nullable=False)

    # Eligibility. SQLite has no array type, so lists are stored comma-separated
    # and exposed as real lists through the properties below.
    # Empty branches/years mean "no restriction"; a null min_cgpa means "no bar".
    eligible_branches = db.Column(db.String(500), nullable=True)
    min_cgpa = db.Column(db.Float, nullable=True)
    eligible_years = db.Column(db.String(200), nullable=True)

    application_deadline = db.Column(db.DateTime, nullable=False, index=True)
    status = db.Column(
        db.Enum(DriveStatus), nullable=False, default=DriveStatus.PENDING, index=True
    )
    rejection_reason = db.Column(db.String(500), nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    company = db.relationship("CompanyProfile", backref="drives")

    @property
    def branch_list(self) -> list[str]:
        return _split_csv(self.eligible_branches)

    @property
    def year_list(self) -> list[int]:
        years = []
        for value in _split_csv(self.eligible_years):
            try:
                years.append(int(value))
            except ValueError:
                continue
        return years

    @property
    def is_past_deadline(self) -> bool:
        # Compared in server-local time — the frame deadlines are stored in.
        from backend.services.timeutils import now as local_now

        return self.application_deadline < local_now()

    @property
    def applicant_count(self) -> int:
        """Number of applications received for this drive."""
        # Imported here rather than at module scope to keep model import order simple.
        from backend.models.application import Application

        if self.id is None:  # not yet persisted
            return 0
        return (
            db.session.query(db.func.count(Application.id))
            .filter(Application.drive_id == self.id)
            .scalar()
            or 0
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "company_name": self.company.company_name if self.company else None,
            "job_title": self.job_title,
            "job_description": self.job_description,
            "eligible_branches": self.branch_list,
            "min_cgpa": self.min_cgpa,
            "eligible_years": self.year_list,
            "application_deadline": (
                self.application_deadline.isoformat() if self.application_deadline else None
            ),
            "status": self.status.value,
            "rejection_reason": self.rejection_reason,
            "is_past_deadline": self.is_past_deadline,
            "applicant_count": self.applicant_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<PlacementDrive {self.id} {self.job_title} ({self.status.value})>"
