"""The public storefront: anyone may reach these pages, signed in or not."""

from __future__ import annotations

from flask import Blueprint, abort, render_template
from sqlalchemy import func, select

from .db import get_session
from .models import Vehicle

bp = Blueprint("public", __name__)


@bp.route("/")
def landing():
    """The storefront's front door: the pitch, the feature cards, three vehicles.

    The featured vehicles are real rows rather than decoration, so the page is
    never selling something the fleet does not have.
    """
    db = get_session()
    featured = db.scalars(
        select(Vehicle)
        .where(Vehicle.is_active.is_(True))
        .where(Vehicle.status == "AVAILABLE")
        .order_by(Vehicle.daily_rate.asc())
        .limit(3)
    ).all()
    available_count = (
        db.scalar(
            select(func.count())
            .select_from(Vehicle)
            .where(Vehicle.is_active.is_(True))
            .where(Vehicle.status == "AVAILABLE")
        )
        or 0
    )

    return render_template(
        "public/landing.html", featured=featured, available_count=available_count
    )


@bp.route("/vehicles")
def browse():
    """The storefront grid. Task 13 gives it its real query and filters."""
    return render_template("public/browse.html", vehicles=[], total=0)


@bp.route("/vehicles/<int:vehicle_id>")
def vehicle_detail(vehicle_id: int):
    """One vehicle as a customer sees it. Task 14 gives it its real content."""
    vehicle = get_session().get(Vehicle, vehicle_id)
    if vehicle is None:
        abort(404)
    return render_template("public/vehicle_detail.html", vehicle=vehicle)
