"""Turning a chosen window into a reservation.

Every price on every page in this flow comes from `scheduling.quote_for`, and
every verdict from `scheduling.availability_for`. Nothing here re-derives a
figure, which is what keeps the live preview, the review page and the committed
reservation in agreement.
"""

from __future__ import annotations

from flask import Blueprint, abort, jsonify, request
from sqlalchemy import select

from . import scheduling
from .auth import current_role
from .db import get_session
from .models import Vehicle

bp = Blueprint("booking", __name__)


def wants(name: str) -> bool:
    """Read a checkbox from the query string or the form.

    A checkbox that is off is simply absent, so presence is the whole test.
    """
    return request.values.get(name) not in (None, "", "0", "false")


def visible_vehicle(vehicle_id: int) -> Vehicle:
    """Load a vehicle a customer is allowed to see, or 404.

    Matches `public.vehicle_detail`: a disabled vehicle is not part of the
    fleet on offer, but stays reachable for an admin.
    """
    vehicle = get_session().get(Vehicle, vehicle_id)
    if vehicle is None:
        abort(404)
    if not vehicle.is_active and current_role() != "admin":
        abort(404)
    return vehicle


@bp.route("/api/quote")
def api_quote():
    """Price one window, as JSON, for the live preview.

    Public on purpose: it prices published rates against a published fleet and
    reveals nothing the detail page does not already show. It reads no session
    and writes nothing.
    """
    vehicle = visible_vehicle(request.args.get("vehicle", type=int) or 0)
    interval = scheduling.parse_window(
        request.args.get("pickup"), request.args.get("return")
    )
    if interval is None:
        return (
            jsonify(
                available=False,
                reason="window",
                message="Choose a pickup date and a return date after it.",
                total=None,
                lines=[],
            ),
            400,
        )

    db = get_session()
    verdict = scheduling.availability_for(db, vehicle, interval)
    if not verdict.ok:
        return jsonify(
            available=False,
            reason=verdict.reason,
            message=verdict.message,
            total=None,
            lines=[],
        )

    result = scheduling.quote_for(
        db,
        vehicle,
        interval,
        want_additional_driver=wants("driver"),
        want_insurance=wants("insurance"),
    )
    return jsonify(
        available=True,
        reason=None,
        message=None,
        total=str(result.total_amount),
        lines=[[label, detail, str(amount)] for label, detail, amount in result.lines],
    )
