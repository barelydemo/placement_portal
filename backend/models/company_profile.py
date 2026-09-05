"""Company profile — 1:1 with a User whose role is COMPANY."""

import enum
from datetime import datetime, timezone

from backend.models import db


class ApprovalStatus(enum.Enum):
    """Admin approval state of a registered company."""

    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class CompanyProfile(db.Model):
    __tablename__ = "company_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False, index=True
    )
    company_name = db.Column(db.String(200), nullable=False)
    hr_contact = db.Column(db.String(120), nullable=True)
    website = db.Column(db.String(255), nullable=True)
    approval_status = db.Column(
        db.Enum(ApprovalStatus), nullable=False, default=ApprovalStatus.PENDING, index=True
    )
    # Set when an admin rejects; cleared again on approval.
    rejection_reason = db.Column(db.String(500), nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    user = db.relationship("User", back_populates="company_profile")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "company_name": self.company_name,
            "hr_contact": self.hr_contact,
            "website": self.website,
            "approval_status": self.approval_status.value,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<CompanyProfile {self.company_name} ({self.approval_status.value})>"
