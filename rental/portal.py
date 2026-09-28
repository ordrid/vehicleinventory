"""The customer's own area. Every page here is scoped to the signed-in customer."""

from __future__ import annotations

from flask import Blueprint, render_template

from .auth import customer_required

bp = Blueprint("portal", __name__, url_prefix="/my")


# An empty rule registers exactly "/my"; see admin/dashboard.py.
@bp.route("")
@customer_required
def dashboard():
    """The customer portal home. Task 17 gives it its real content."""
    return render_template("customer/dashboard.html")
