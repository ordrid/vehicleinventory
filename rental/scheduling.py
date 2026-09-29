"""Where database rows meet the pure domain functions.

`rental/domain/` takes plain values and returns plain values; it imports
neither Flask nor SQLAlchemy, and `scripts/check-domain-purity.py` keeps it
that way. Something has to turn rows into those values, and this is it.

Routes call this module. They never import `rental.domain` directly -- which is
what makes the live preview, the review page and the commit three callers of
one calculation rather than three implementations that drift apart.

This module takes a session and plain arguments, so it can be tested without an
app context. It must not import Flask.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from .domain.availability import Availability, Interval, check
from .domain.pricing import Quote, Rates, quote
from .models import Rental, RentalRates, Reservation, Vehicle

#: A reservation in one of these states holds the slot. "First request holds it"
#: is the reason PENDING is here: an unconfirmed request still blocks others.
BLOCKING_RESERVATION_STATUSES: tuple[str, ...] = ("PENDING", "CONFIRMED")

#: A vehicle that is out on an ACTIVE rental is not available, whatever its
#: reservation says.
BLOCKING_RENTAL_STATUSES: tuple[str, ...] = ("ACTIVE",)

#: What an <input type="datetime-local"> submits.
WINDOW_FORMAT = "%Y-%m-%dT%H:%M"


def parse_window(pickup: str | None, return_: str | None) -> Interval | None:
    """Turn two form values into an Interval, or None when they are unusable.

    Returning None rather than raising is deliberate: a half-filled or
    nonsensical date pair is the normal state of the browse page before the
    customer has chosen anything, not an error to report.
    """
    if not pickup or not return_:
        return None
    try:
        start = datetime.strptime(pickup, WINDOW_FORMAT)
        end = datetime.strptime(return_, WINDOW_FORMAT)
    except ValueError:
        return None
    if end <= start:
        return None
    return Interval(start, end)


def blocked_intervals(
    db, vehicle: Vehicle, *, exclude_reservation_id: int | None = None
) -> list[Interval]:
    """Every window this vehicle is already spoken for.

    `exclude_reservation_id` leaves out the reservation being re-examined, so a
    booking is never found to conflict with itself.
    """
    reservations = select(Reservation).where(
        Reservation.vehicle_id == vehicle.id,
        Reservation.status.in_(BLOCKING_RESERVATION_STATUSES),
    )
    if exclude_reservation_id is not None:
        reservations = reservations.where(Reservation.id != exclude_reservation_id)

    rentals = select(Rental).where(
        Rental.vehicle_id == vehicle.id,
        Rental.status.in_(BLOCKING_RENTAL_STATUSES),
    )
    if exclude_reservation_id is not None:
        rentals = rentals.where(Rental.reservation_id != exclude_reservation_id)

    blocked = [
        Interval(row.pickup_at, row.return_at) for row in db.scalars(reservations).all()
    ]
    blocked += [
        Interval(row.actual_pickup, row.actual_return or row.expected_return)
        for row in db.scalars(rentals).all()
    ]
    return blocked


def current_rates(db) -> Rates:
    """The one RentalRates row, as the domain's plain-value Rates."""
    row = RentalRates.current(db)
    return Rates(
        additional_driver_fee_per_day=row.additional_driver_fee_per_day,
        insurance_fee_per_day=row.insurance_fee_per_day,
        late_fee_per_day=row.late_fee_per_day,
    )


def availability_for(db, vehicle: Vehicle, interval: Interval) -> Availability:
    """Can this vehicle be booked for this window?

    `vehicle.status` describes the vehicle *right now*. Only MAINTENANCE blocks
    a future window; RESERVED and RENTED are answered by date overlap instead,
    which is why they are normalised away here.
    """
    status = vehicle.status if vehicle.status == "MAINTENANCE" else "AVAILABLE"
    return check(
        interval,
        is_active=vehicle.is_active,
        status=status,
        blocked=blocked_intervals(db, vehicle),
    )


def quote_for(
    db,
    vehicle: Vehicle,
    interval: Interval,
    *,
    want_additional_driver: bool,
    want_insurance: bool,
) -> Quote:
    """What this vehicle costs for this window, itemised."""
    return quote(
        interval.start,
        interval.end,
        daily_rate=vehicle.daily_rate,
        hourly_rate=vehicle.hourly_rate,
        rates=current_rates(db),
        want_additional_driver=want_additional_driver,
        want_insurance=want_insurance,
    )
