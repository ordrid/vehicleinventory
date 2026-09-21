"""Shared pytest fixtures: a fresh in-memory SQLite database for every test."""

from __future__ import annotations

from datetime import date

import pytest

from inventory import create_app
from inventory.db import get_engine, get_session
from inventory.models import Base, User, Vehicle

TEST_CONFIG = {
    # "sqlite://" is an in-memory database. db.create_db_engine gives it a
    # StaticPool so the whole test shares one connection.
    "DATABASE_URL": "sqlite://",
    "TESTING": True,
    "SECRET_KEY": "test-secret",
    # Turning CSRF off lets the tests post plain dictionaries. The tokens
    # themselves are Flask-WTF's job, not this project's.
    "WTF_CSRF_ENABLED": False,
}


@pytest.fixture
def app():
    """Build an app backed by an empty in-memory database with one known user."""
    app = create_app(TEST_CONFIG)

    with app.app_context():
        Base.metadata.create_all(get_engine())
        db = get_session()
        user = User(username="admin")
        user.set_password("secret123")
        db.add(user)
        db.commit()

    yield app


@pytest.fixture
def client(app):
    """A test client that is not logged in."""
    return app.test_client()


@pytest.fixture
def auth_client(app):
    """A test client that has already logged in as 'admin'."""
    client = app.test_client()
    client.post("/login", data={"username": "admin", "password": "secret123"})
    return client


@pytest.fixture
def sample_vehicle(app):
    """Insert one vehicle and return its id."""
    with app.app_context():
        db = get_session()
        vehicle = Vehicle(
            plate_number="ABC 1234",
            make="Toyota",
            model="Hilux",
            year=2021,
            vehicle_type="Pickup",
            color="White",
            status="Available",
            date_acquired=date(2021, 3, 15),
        )
        db.add(vehicle)
        db.commit()
        return vehicle.id
