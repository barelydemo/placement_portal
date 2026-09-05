"""Unified User model — one table for admin, company and student accounts."""

import enum
from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from backend.models import db


class UserRole(enum.Enum):
    """The three roles of the portal. Admin is seeded, never registered."""

    ADMIN = "admin"
    COMPANY = "company"
    STUDENT = "student"


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # 1:1 profiles — exactly one of these is populated, based on `role`.
    company_profile = db.relationship(
        "CompanyProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    student_profile = db.relationship(
        "StudentProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def profile(self):
        """Return the profile matching this user's role (None for admin)."""
        if self.role is UserRole.COMPANY:
            return self.company_profile
        if self.role is UserRole.STUDENT:
            return self.student_profile
        return None

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role.value,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<User {self.id} {self.email} ({self.role.value})>"
