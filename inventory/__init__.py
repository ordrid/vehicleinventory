"""Application factory for the Vehicle Inventory System."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, session, url_for
from flask_wtf.csrf import CSRFError, CSRFProtect

from . import auth, cli, db, reports, theme, vehicles
from .forms import max_year
from .models import STATUS_BADGES, STATUSES, VEHICLE_TYPES

# Load .env for local development. On Vercel the variables are already in the
# environment, and load_dotenv simply finds no file and does nothing.
load_dotenv()


def create_app(config: dict | None = None) -> Flask:
    """Build and configure the Flask application.

    ``config`` lets the tests override settings (an in-memory database, CSRF
    switched off) without touching the environment. No tables are created here:
    that is what ``flask init-db`` is for.
    """
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    app.config["DATABASE_URL"] = db.get_database_url()
    if config:
        app.config.update(config)

    # Protects every POST in the app and makes csrf_token() available in templates.
    CSRFProtect(app)

    db.init_app(app)
    app.register_blueprint(auth.bp)
    app.register_blueprint(vehicles.bp)
    app.register_blueprint(reports.bp)
    app.register_blueprint(theme.bp)
    cli.register_cli(app)
    register_template_globals(app)
    register_error_handlers(app)

    return app


def register_template_globals(app: Flask) -> None:
    """Make the shared option lists and the current user available to every template."""

    @app.context_processor
    def inject_globals():
        return {
            "STATUSES": STATUSES,
            "VEHICLE_TYPES": VEHICLE_TYPES,
            "STATUS_BADGES": STATUS_BADGES,
            "current_username": session.get("username"),
            "max_year": max_year(),
            # Which theme button to highlight, and what to put in data-theme.
            "theme_choice": theme.current_choice(),
            "theme_name": theme.current_theme_name(),
        }


def register_error_handlers(app: Flask) -> None:
    """Show friendly pages instead of Flask's default error output."""

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        """Handle an expired or missing CSRF token with a message instead of a bare 400.

        This happens when a page has been left open long enough for the session
        cookie to expire. Sending the visitor back to the dashboard (which
        bounces to the login page when they are signed out) is friendlier than
        Flask-WTF's default error page.
        """
        flash("Your session expired. Please try that again.", "warning")
        return redirect(url_for("vehicles.dashboard"))

    @app.errorhandler(404)
    def not_found(error):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(error):
        # The session may be in a broken state after a database error.
        db.close_session()
        return render_template("500.html"), 500
