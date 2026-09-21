"""Flask CLI commands for setting the database up.

Tables are deliberately never created when the app starts: on Vercel the app is
imported on every cold start, and running DDL there would be slow and unsafe.
These commands are run by hand from a laptop instead, pointed at Neon.
"""

from __future__ import annotations

from datetime import date

import click
from flask import Flask
from flask.cli import with_appcontext
from sqlalchemy import select

from .db import get_engine, get_session
from .models import Base, User, Vehicle

# ~15 vehicles used for demos and screenshots.
SAMPLE_VEHICLES = [
    ("ABC 1234", "Toyota", "Hilux", 2021, "Pickup", "White", "Available", date(2021, 3, 15), "Assigned to field operations."),
    ("XYZ 5678", "Toyota", "Vios", 2019, "Sedan", "Silver", "In Use", date(2019, 7, 2), ""),
    ("JKL 2468", "Mitsubishi", "Montero Sport", 2022, "SUV", "Black", "Available", date(2022, 1, 20), ""),
    ("MNO 1357", "Isuzu", "D-Max", 2018, "Pickup", "Blue", "Under Maintenance", date(2018, 11, 5), "Scheduled for brake replacement."),
    ("PQR 8642", "Nissan", "Urvan", 2020, "Van", "White", "In Use", date(2020, 5, 12), "Staff shuttle."),
    ("STU 9753", "Honda", "Civic", 2017, "Sedan", "Red", "Retired", date(2017, 2, 28), "Replaced in 2024."),
    ("VWX 3141", "Ford", "Ranger", 2023, "Pickup", "Grey", "Available", date(2023, 6, 9), ""),
    ("YZA 5926", "Hyundai", "Starex", 2016, "Van", "Silver", "Under Maintenance", date(2016, 9, 30), "Aircon repair."),
    ("BCD 5358", "Suzuki", "Ertiga", 2021, "SUV", "Maroon", "In Use", date(2021, 10, 18), ""),
    ("EFG 9793", "Yamaha", "Mio i 125", 2022, "Motorcycle", "Blue", "Available", date(2022, 4, 4), "Used for errands."),
    ("HIJ 2384", "Honda", "TMX 125", 2015, "Motorcycle", "Black", "Retired", date(2015, 8, 21), "Beyond economical repair."),
    ("KLM 6264", "Hino", "300 Series", 2019, "Truck", "White", "Available", date(2019, 12, 1), "Delivery truck."),
    ("NOP 3383", "Fuso", "Canter", 2020, "Truck", "Blue", "In Use", date(2020, 3, 17), ""),
    ("QRS 2795", "Toyota", "Fortuner", 2024, "SUV", "Pearl White", "Available", date(2024, 2, 14), "Executive vehicle."),
    ("TUV 0288", "Mitsubishi", "L300", 2014, "Van", "White", "Under Maintenance", None, "Engine overhaul, date of purchase unknown."),
]


def register_cli(app: Flask) -> None:
    """Attach the three custom commands to the Flask app."""
    app.cli.add_command(init_db_command)
    app.cli.add_command(create_admin_command)
    app.cli.add_command(seed_command)


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Create the users and vehicles tables if they do not exist yet."""
    Base.metadata.create_all(get_engine())
    click.echo("Tables created.")


@click.command("create-admin")
@click.option("--username", prompt=True, help="Username for the new account.")
@click.password_option(help="Password for the new account.")
@with_appcontext
def create_admin_command(username: str, password: str):
    """Create a login account, storing the password as a werkzeug hash."""
    db = get_session()
    username = username.strip()

    if db.scalars(select(User).where(User.username == username)).first():
        click.echo(f"User {username!r} already exists.")
        return

    user = User(username=username)
    user.set_password(password)
    db.add(user)
    db.commit()
    click.echo(f"Created user {username!r}.")


@click.command("seed")
@with_appcontext
def seed_command():
    """Insert the sample vehicles, skipping any plate that is already in the table."""
    db = get_session()
    added = 0

    for plate, make, model, year, vtype, color, status, acquired, remarks in SAMPLE_VEHICLES:
        if db.scalars(select(Vehicle).where(Vehicle.plate_number == plate)).first():
            continue
        db.add(
            Vehicle(
                plate_number=plate,
                make=make,
                model=model,
                year=year,
                vehicle_type=vtype,
                color=color,
                status=status,
                date_acquired=acquired,
                remarks=remarks or None,
            )
        )
        added += 1

    db.commit()
    click.echo(f"Added {added} sample vehicle(s).")
