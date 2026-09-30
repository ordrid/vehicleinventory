"""The reservation queue: accept a request, or decline it.

Each action calls the matching phase 2 function and applies the StateChange it
returns, so the reservation and the vehicle move together or not at all. The
mapping of "what does confirming change" lives in `domain/lifecycle.py`, not
here -- this module is the transaction around it.
"""

from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, url_for
from sqlalchemy import select

from ..auth import admin_required
from ..db import get_session
from ..domain.lifecycle import StateChange, TransitionError, confirm_reservation, reject_reservation
from ..models import Reservation, User, Vehicle

bp = Blueprint("admin_reservations", __name__, url_prefix="/admin/reservations")

#: The queue's own order: waiting requests first, then the rest, newest first.
QUEUE_FIRST = ("PENDING", "CONFIRMED")


def load_reservation(reservation_id: int) -> Reservation:
    """Load one reservation for an admin, or 404."""
    reservation = get_session().get(Reservation, reservation_id)
    if reservation is None:
        abort(404)
    return reservation


def apply_change(db, reservation: Reservation, change: StateChange, rental=None) -> None:
    """Write a StateChange across every row it names, in one transaction.

    Requirement 18's five-part close is one value returned by the domain; this
    is the only place that turns it into writes, so a route cannot perform four
    of the five.
    """
    reservation.status = change.reservation_status
    db.get(Vehicle, reservation.vehicle_id).status = change.vehicle_status
    if change.rental_status is not None and rental is not None:
        rental.status = change.rental_status
    db.commit()


# An empty rule registers exactly "/admin/reservations"; see admin/dashboard.py.
@bp.route("")
@admin_required
def queue():
    """Every reservation, with the ones waiting on a decision at the top.

    Neither `Reservation.user` nor `Reservation.vehicle` is a relationship --
    the models declare none -- so both the customer and the vehicle are joined
    explicitly here rather than via `joinedload`, and the template unpacks the
    (Reservation, User, Vehicle) triple instead of walking an attribute.
    """
    db = get_session()
    rows = db.execute(
        select(Reservation, User, Vehicle)
        .join(User, User.id == Reservation.user_id)
        .join(Vehicle, Vehicle.id == Reservation.vehicle_id)
        .order_by(Reservation.created_at.desc(), Reservation.id.desc())
    ).all()
    return render_template(
        "admin/reservations.html",
        pending=[row for row in rows if row[0].status == "PENDING"],
        others=[row for row in rows if row[0].status != "PENDING"],
    )


def decide(reservation_id: int, action, verb: str):
    """Shared body for confirm and reject.

    A TransitionError here means the page was stale -- two admins working at
    once -- which is a message, not a 500.
    """
    reservation = load_reservation(reservation_id)
    db = get_session()
    try:
        change = action(reservation.status)
    except TransitionError as error:
        flash(str(error), "warning")
        return redirect(url_for("admin_reservations.queue"))

    apply_change(db, reservation, change)
    flash(f"Reservation {reservation.reservation_number} was {verb}.", "success")
    return redirect(url_for("admin_reservations.queue"))


@bp.route("/<int:reservation_id>/confirm", methods=["POST"])
@admin_required
def confirm(reservation_id: int):
    """Accept a pending request. The vehicle is now spoken for."""
    return decide(reservation_id, confirm_reservation, "confirmed")


@bp.route("/<int:reservation_id>/reject", methods=["POST"])
@admin_required
def reject(reservation_id: int):
    """Decline a pending request and release the vehicle."""
    return decide(reservation_id, reject_reservation, "rejected")
