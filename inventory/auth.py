"""Sign-up, login, logout and the decorator that protects every other page."""

from __future__ import annotations

from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from sqlalchemy import select

from .db import get_session
from .forms import LoginForm, SignupForm
from .models import User

bp = Blueprint("auth", __name__)


def login_required(view):
    """Redirect anonymous visitors to the login page instead of running the view.

    Wraps a route function. If there is no ``user_id`` in the Flask session the
    request is bounced to the login page, remembering where the user was headed
    so they land there after signing in.
    """

    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped_view


def find_user_by_username(username: str) -> User | None:
    """Look up a single user by username, or return None when there is no match."""
    db = get_session()
    return db.scalars(select(User).where(User.username == username)).first()


def find_user_by_email(email: str) -> User | None:
    """Look up a single user by email address, or return None when there is no match."""
    db = get_session()
    return db.scalars(select(User).where(User.email == email)).first()


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Show the login form and sign the user in when the credentials are correct.

    On POST the username is looked up and the submitted password is compared
    against the stored hash. A wrong username and a wrong password give the same
    message on purpose, so the form cannot be used to discover valid usernames.
    On success the user's id is stored in the signed session cookie.
    """
    if session.get("user_id"):
        return redirect(url_for("vehicles.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        user = find_user_by_username(form.username.data.strip())
        if user is not None and user.check_password(form.password.data):
            session.clear()
            session["user_id"] = user.id
            session["username"] = user.username
            flash("Signed in successfully.", "success")
            return redirect(safe_next_page(request.args.get("next")))
        flash("Invalid username or password.", "error")

    return render_template("login.html", form=form)


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    """Show the sign-up form and create the account when everything validates.

    There is no email confirmation step: the address is only stored so an
    account can be identified later. Username and email are both unique, and
    each clash is reported on its own field so the visitor knows which to
    change. A new account is signed in straight away.
    """
    if session.get("user_id"):
        return redirect(url_for("vehicles.dashboard"))

    form = SignupForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data

        if find_user_by_username(username) is not None:
            form.username.errors.append("That username is already taken.")
        if find_user_by_email(email) is not None:
            form.email.errors.append("That email address already has an account.")

        if not form.errors:
            db = get_session()
            user = User(username=username, email=email)
            user.set_password(form.password.data)
            db.add(user)
            db.commit()

            session.clear()
            session["user_id"] = user.id
            session["username"] = user.username
            flash(f"Welcome, {user.username}! Your account is ready.", "success")
            return redirect(url_for("vehicles.dashboard"))

    return render_template("signup.html", form=form)


@bp.route("/logout", methods=["POST"])
def logout():
    """Clear the session and send the user back to the login page."""
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))


def safe_next_page(target: str | None) -> str:
    """Return a safe redirect target, ignoring anything pointing off this site.

    Only paths beginning with a single ``/`` are accepted, which blocks
    ``//evil.com`` and full URLs from being used as an open redirect.
    """
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for("vehicles.dashboard")
