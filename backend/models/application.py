"""A student's application to a placement drive."""

import enum
from datetime import datetime, timezone

from backend.models import db


class ApplicationStatus(enum.Enum):
    APPLIED = "Applied"
    SHORTLISTED = "Shortlisted"
    SELECTED = "Selected"
    REJECTED = "Rejected"


class Application(db.Model):
    __tablename__ = "applications"
    __table_args__ = (
        # Belt and braces against double applications: the service checks first,
        # but this makes a duplicate impossible even under a race or direct write.
        db.UniqueConstraint("student_id", "drive_id", name="uq_application_student_drive"),
    )

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("student_profiles.id"), nullable=False, index=True
    )
    drive_id = db.Column(
        db.Integer, db.ForeignKey("placement_drives.id"), nullable=False, index=True
    )
    status = db.Column(
        db.Enum(ApplicationStatus), nullable=False, default=ApplicationStatus.APPLIED, index=True
    )
    interview_datetime = db.Column(db.DateTime, nullable=True)
    applied_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(db.DateTime, nullable=True)

    student = db.relationship("StudentProfile", backref="applications")
    drive = db.relationship("PlacementDrive", backref="applications")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "student_id": self.student_id,
            "drive_id": self.drive_id,
            "status": self.status.value,
            "interview_datetime": (
                self.interview_datetime.isoformat() if self.interview_datetime else None
            ),
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<Application {self.id} student={self.student_id} drive={self.drive_id}>"
