"""Sign-up, login, logout, guest access and the decorators that guard every other page."""

from __future__ import annotations

from functools import wraps

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import select

from .db import get_session
from .forms import LoginForm, SignupForm
from .models import User

bp = Blueprint("auth", __name__)


def current_role() -> str | None:
    """Return "user" for a signed-in account, "guest" for a read-only visitor, None otherwise.

    The role is worked out from what is already in the session rather than
    stored as a third key, so a session created before guest access existed
    still reports the right role.
    """
    if session.get("user_id"):
        return "user"
    if session.get("guest"):
        return "guest"
    return None


def viewer_required(view):
    """Allow signed-in users and guests through; send anonymous visitors to the login page.

    Wraps a route function. This is the guard for every read-only page. When
    there is no session at all the request is bounced to the login page,
    remembering where the visitor was headed so they land there afterwards.
    """

    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if current_role() is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped_view


def editor_required(view):
    """Allow only signed-in users through; a guest gets a 403.

    This is the guard for every page that changes data. A guest is refused
    outright rather than redirected, because they already have a session and
    bouncing them to a login form they did not ask for would be confusing.
    """

    @wraps(view)
    def wrapped_view(*args, **kwargs):
        role = current_role()
        if role is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        if role != "user":
            abort(403)
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


@bp.route("/guest", methods=["POST"])
def guest():
    """Start a read-only session with no account behind it.

    Nothing is written to the database: the guest is simply a session that has
    no ``user_id``, which every ``editor_required`` route refuses. POST rather
    than GET because it changes the session, so a link or a crawler cannot put
    a signed-in user into guest mode.
    """
    session.clear()
    session["guest"] = True
    flash("You are browsing in read-only mode.", "info")
    return redirect(url_for("vehicles.dashboard"))


@bp.route("/logout", methods=["POST"])
def logout():
    """Clear the session and send the visitor back to the login page.

    Used both by the Log out button and by the guest's Exit guest button, since
    ending either kind of session means the same thing: throw it away.
    """
    was_guest = current_role() == "guest"
    session.clear()
    flash("You have left guest mode." if was_guest else "You have been logged out.", "success")
    return redirect(url_for("auth.login"))


def safe_next_page(target: str | None) -> str:
    """Return a safe redirect target, ignoring anything pointing off this site.

    Only paths beginning with a single ``/`` are accepted, which blocks
    ``//evil.com`` and full URLs from being used as an open redirect.
    """
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for("vehicles.dashboard")
