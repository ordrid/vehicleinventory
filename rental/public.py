"""The public storefront: anyone may reach these pages, signed in or not."""

from __future__ import annotations

from flask import Blueprint, abort, render_template

from .db import get_session
from .models import Vehicle

bp = Blueprint("public", __name__)


@bp.route("/")
def landing():
    """The front page. Task 12 gives it its real content."""
    return render_template("public/landing.html")


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
