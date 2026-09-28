"""Flask-WTF forms. Flask-WTF also gives every form CSRF protection for free."""

from __future__ import annotations

from datetime import date

from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, EqualTo, Length, NumberRange, Optional, Regexp

from .models import STATUSES, VEHICLE_TYPES

MIN_YEAR = 1950

# Deliberately loose: "something@something.tld". A stricter check would need the
# email-validator package, and the only real proof an address works is sending
# to it, which this app does not do yet.
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$"
MIN_PASSWORD_LENGTH = 8


def max_year() -> int:
    """Newest model year we accept: next year, since dealers sell ahead of the calendar."""
    return date.today().year + 1


def clean_plate(value: str | None) -> str | None:
    """Trim surrounding spaces and upper-case a plate number so ' abc 123 ' becomes 'ABC 123'."""
    if value is None:
        return None
    return value.strip().upper()


def clean_email(value: str | None) -> str | None:
    """Trim and lower-case an address so 'Me@Example.COM ' and 'me@example.com' are one account."""
    if value is None:
        return None
    return value.strip().lower()


def clean_text(value: str | None) -> str | None:
    """Trim surrounding spaces; turn an empty string into None so the column stays NULL."""
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


class LoginForm(FlaskForm):
    """Username and password for signing in."""

    username = StringField("Username", validators=[DataRequired(), Length(max=80)])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log in")


class SignupForm(FlaskForm):
    """Create a new account: username, email address and a password typed twice."""

    username = StringField(
        "Username",
        filters=[clean_text],
        validators=[
            DataRequired(message="Username is required."),
            Length(min=3, max=80, message="Username must be between 3 and 80 characters."),
            Regexp(
                r"^[A-Za-z0-9._-]+$",
                message="Username may only contain letters, numbers, dots, dashes and underscores.",
            ),
        ],
    )
    email = StringField(
        "Email",
        filters=[clean_email],
        validators=[
            DataRequired(message="Email is required."),
            Length(max=255),
            Regexp(EMAIL_PATTERN, message="Enter a valid email address."),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Password is required."),
            Length(
                min=MIN_PASSWORD_LENGTH,
                message=f"Password must be at least {MIN_PASSWORD_LENGTH} characters.",
            ),
        ],
    )
    confirm_password = PasswordField(
        "Confirm password",
        validators=[
            DataRequired(message="Please retype the password."),
            EqualTo("password", message="The two passwords do not match."),
        ],
    )
    submit = SubmitField("Create account")


class VehicleForm(FlaskForm):
    """Add / edit form for a vehicle. The same validation rules apply to both pages."""

    plate_number = StringField(
        "Plate number",
        filters=[clean_plate],
        validators=[DataRequired(message="Plate number is required."), Length(max=20)],
    )
    make = StringField(
        "Make",
        filters=[clean_text],
        validators=[DataRequired(message="Make is required."), Length(max=50)],
    )
    model = StringField(
        "Model",
        filters=[clean_text],
        validators=[DataRequired(message="Model is required."), Length(max=50)],
    )
    year = IntegerField("Year", validators=[DataRequired(message="Year is required.")])
    vehicle_type = SelectField(
        "Type",
        choices=[(t, t) for t in VEHICLE_TYPES],
        validators=[DataRequired()],
    )
    color = StringField("Color", filters=[clean_text], validators=[Optional(), Length(max=30)])
    status = SelectField(
        "Status",
        choices=[(s, s) for s in STATUSES],
        validators=[DataRequired()],
    )
    date_acquired = DateField("Date acquired", validators=[Optional()])
    remarks = TextAreaField("Remarks", filters=[clean_text], validators=[Optional()])
    submit = SubmitField("Save vehicle")

    def __init__(self, *args, **kwargs):
        """Set the year range here so the upper bound follows the real calendar year."""
        super().__init__(*args, **kwargs)
        self.year.validators = [
            DataRequired(message="Year is required."),
            NumberRange(
                min=MIN_YEAR,
                max=max_year(),
                message=f"Year must be between {MIN_YEAR} and {max_year()}.",
            ),
        ]


class DeleteForm(FlaskForm):
    """Empty form used only to carry a CSRF token on the delete confirmation page."""

    submit = SubmitField("Yes, delete it")
