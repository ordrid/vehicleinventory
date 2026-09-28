"""The customer's own area. Every page here is scoped to the signed-in customer."""

from __future__ import annotations

from flask import Blueprint, render_template
from sqlalchemy import func, select

from .auth import current_user, customer_required
from .db import get_session
from .models import Rental, Reservation, Vehicle

bp = Blueprint("portal", __name__, url_prefix="/my")


# An empty rule registers exactly "/my"; see admin/dashboard.py.
@bp.route("")
@customer_required
def dashboard():
    """The customer's own summary: what is on offer, and what they have booked.

    Every count is scoped to the signed-in customer. Reservation and rental
    figures are legitimately zero until phase 3 provides a way to create one.
    """
    db = get_session()
    user = current_user()

    available = db.scalar(
        select(func.count())
        .select_from(Vehicle)
        .where(Vehicle.is_active.is_(True))
        .where(Vehicle.status == "AVAILABLE")
    ) or 0
    my_reservations = db.scalar(
        select(func.count())
        .select_from(Reservation)
        .where(Reservation.user_id == user.id)
        .where(Reservation.status.in_(["PENDING", "CONFIRMED"]))
    ) or 0
    active_rental = db.scalar(
        select(func.count())
        .select_from(Rental)
        .where(Rental.customer_id == user.id)
        .where(Rental.status == "ACTIVE")
    ) or 0
    total_rentals = db.scalar(
        select(func.count()).select_from(Rental).where(Rental.customer_id == user.id)
    ) or 0

    return render_template(
        "customer/dashboard.html",
        available=available,
        my_reservations=my_reservations,
        active_rental=active_rental,
        total_rentals=total_rentals,
    )
