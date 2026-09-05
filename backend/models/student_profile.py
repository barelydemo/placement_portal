"""Student profile — 1:1 with a User whose role is STUDENT."""

from datetime import datetime, timezone

from backend.models import db


class StudentProfile(db.Model):
    __tablename__ = "student_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False, index=True
    )
    # Eligibility fields — drives filter on these from Phase 4 onwards.
    branch = db.Column(db.String(100), nullable=True)
    cgpa = db.Column(db.Float, nullable=True)
    graduation_year = db.Column(db.Integer, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    resume_path = db.Column(db.String(255), nullable=True)
    resume_original_name = db.Column(db.String(255), nullable=True)
    resume_uploaded_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    user = db.relationship("User", back_populates="student_profile")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "branch": self.branch,
            "cgpa": self.cgpa,
            "graduation_year": self.graduation_year,
            "phone": self.phone,
            "has_resume": bool(self.resume_path),
            "resume_name": self.resume_original_name,
            "resume_uploaded_at": (
                self.resume_uploaded_at.isoformat() if self.resume_uploaded_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<StudentProfile user_id={self.user_id} branch={self.branch}>"
