"""SQLAlchemy models: the login accounts and the vehicles being tracked."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from werkzeug.security import check_password_hash, generate_password_hash

# The fixed option lists used by the forms, the filters and the reports.
VEHICLE_TYPES = ["Sedan", "SUV", "Pickup", "Van", "Truck", "Motorcycle"]
STATUSES = ["Available", "In Use", "Under Maintenance", "Retired"]

# The status pill colour for each status. Kept deliberately far apart in hue
# so the four states stay easy to tell apart, including in a printout.
STATUS_BADGES = {
    "Available": "pill-green",
    "In Use": "pill-blue",
    "Under Maintenance": "pill-amber",
    "Retired": "pill-slate",
}


def utcnow() -> datetime:
    """Return the current UTC time (used as the default for timestamp columns)."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class every model inherits from."""


class User(Base):
    """A person who can log in and manage the inventory."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    def set_password(self, password: str) -> None:
        """Hash the given plain-text password and store it. The password itself is never saved."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Return True when the plain-text password matches the stored hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class Vehicle(Base):
    """One vehicle in the inventory."""

    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plate_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    make: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(50), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    vehicle_type: Mapped[str] = mapped_column(String(20), nullable=False)
    color: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Available")
    date_acquired: Mapped[date | None] = mapped_column(Date, nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    @property
    def badge_class(self) -> str:
        """Return the status pill colour class that matches this vehicle's status."""
        return STATUS_BADGES.get(self.status, "pill-slate")

    def __repr__(self) -> str:
        return f"<Vehicle {self.plate_number} {self.make} {self.model}>"
