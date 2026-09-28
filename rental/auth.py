"""Sign-up, login, logout, and the decorators that guard every other page."""

from __future__ import annotations

from functools import wraps

from flask import (
    Blueprint,
    abort,
    flash,
    g,
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


def current_user() -> User | None:
    """Return the signed-in User, or None. Loaded once per request and cached on g.

    The role is read off the row rather than stored in the cookie, so an admin
    who is demoted loses access on their next request rather than at their next
    login.
    """
    if "current_user" not in g:
        user_id = session.get("user_id")
        g.current_user = get_session().get(User, user_id) if user_id else None
    return g.current_user


def current_role() -> str | None:
    """Return "admin", "customer", or None when nobody is signed in."""
    user = current_user()
    return user.role if user else None


def _require(view, predicate):
    """Shared body for the three decorators: redirect anonymous, 403 the wrong role."""

    @wraps(view)
    def wrapped_view(*args, **kwargs):
        user = current_user()
        if user is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        if not predicate(user):
            abort(403)
        return view(*args, **kwargs)

    return wrapped_view


def login_required(view):
    """Any signed-in account. Anonymous visitors go to the login page."""
    return _require(view, lambda user: True)


def admin_required(view):
    """Admins only. A customer gets a 403."""
    return _require(view, lambda user: user.role == "admin")


def customer_required(view):
    """Customers only. An admin gets a 403, because these pages show 'your' rows."""
    return _require(view, lambda user: user.role == "customer")


def find_user_by_username(username: str) -> User | None:
    """Look up a single user by username, or return None when there is no match."""
    db = get_session()
    return db.scalars(select(User).where(User.username == username)).first()


def find_user_by_email(email: str) -> User | None:
    """Look up a single user by email address, or return None when there is no match."""
    db = get_session()
    return db.scalars(select(User).where(User.email == email)).first()


def home_for(user: User) -> str:
    """Where a freshly signed-in person belongs after signing in.

    Both roles land on the same page for now. Task 11 splits this into the
    admin console and the customer portal, once those blueprints exist. It is
    deliberately a function so that change is one line in one place.
    """
    return url_for("vehicles.dashboard")


def safe_next_page(target: str | None, user: User) -> str:
    """Return a safe redirect target, ignoring anything pointing off this site.

    Only paths beginning with a single ``/`` are accepted, which blocks
    ``//evil.com`` and full URLs from being used as an open redirect.
    """
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return home_for(user)


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Show the login form and sign the user in when the credentials are correct.

    On POST the username is looked up and the submitted password is compared
    against the stored hash. A wrong username and a wrong password give the same
    message on purpose, so the form cannot be used to discover valid usernames.
    On success the user's id is stored in the signed session cookie.
    """
    if session.get("user_id"):
        user = current_user()
        if user is not None:
            return redirect(home_for(user))

    form = LoginForm()
    if form.validate_on_submit():
        user = find_user_by_username(form.username.data.strip())
        if user is not None and user.check_password(form.password.data):
            if not user.is_active:
                flash("That account has been disabled. Please contact the office.", "error")
                return render_template("login.html", form=form)
            session.clear()
            session["user_id"] = user.id
            session["username"] = user.username
            flash("Signed in successfully.", "success")
            return redirect(safe_next_page(request.args.get("next"), user))
        flash("Invalid username or password.", "error")

    return render_template("login.html", form=form)


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    """Show the sign-up form and create the account when everything validates.

    There is no email confirmation step: the address is only stored so an
    account can be identified later. Username and email are both unique, and
    each clash is reported on its own field so the visitor knows which to
    change. A new account is signed in straight away, as a customer.
    """
    if session.get("user_id"):
        user = current_user()
        if user is not None:
            return redirect(home_for(user))

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
            user = User(username=username, email=email, role="customer")
            user.full_name = form.full_name.data
            user.phone = form.phone.data
            user.set_password(form.password.data)
            db.add(user)
            db.commit()

            session.clear()
            session["user_id"] = user.id
            session["username"] = user.username
            flash(f"Welcome, {user.username}! Your account is ready.", "success")
            return redirect(home_for(user))

    return render_template("signup.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """Clear the session and send the visitor back to the login page."""
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))
