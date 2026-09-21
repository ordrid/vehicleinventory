"""Light / dark theme switching, stored in the Flask session.

There is no JavaScript involved. Clicking a theme button submits a small POST
form; the choice is kept in the session cookie and every page then renders the
matching ``data-theme`` attribute on the ``<html>`` element.
"""

from __future__ import annotations

from flask import Blueprint, redirect, request, session

from .auth import safe_next_page

bp = Blueprint("theme", __name__)

# What the user picks -> the daisyUI theme to put in data-theme.
# "auto" maps to None: with no data-theme attribute at all, the stylesheet's
# own "prefers-color-scheme: dark" rule takes over and follows the system.
THEME_CHOICES = {
    "auto": None,
    "light": "emerald",
    "dark": "forest",
}

DEFAULT_CHOICE = "auto"


def current_choice() -> str:
    """Return the visitor's theme choice: 'auto', 'light' or 'dark'.

    Anything unexpected in the session falls back to 'auto', so a tampered or
    outdated cookie can never put an unknown value into the page.
    """
    choice = session.get("theme", DEFAULT_CHOICE)
    return choice if choice in THEME_CHOICES else DEFAULT_CHOICE


def current_theme_name() -> str | None:
    """Return the daisyUI theme name to render, or None when following the system."""
    return THEME_CHOICES[current_choice()]


@bp.route("/theme", methods=["POST"])
def set_theme():
    """Save the requested theme in the session and return to the page you came from.

    The theme is stored per browser session rather than per user account, so it
    also works on the login page before anyone has signed in.
    """
    requested = request.form.get("theme", DEFAULT_CHOICE)
    session["theme"] = requested if requested in THEME_CHOICES else DEFAULT_CHOICE
    return redirect(safe_next_page(request.form.get("next")))
