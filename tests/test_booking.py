"""The booking flow's routes."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from rental.db import get_session
from rental.models import RentalRates, Reservation, User, Vehicle

JAN10 = "2026-01-10T09:00"
JAN12 = "2026-01-12T09:00"


@pytest.fixture
def vehicle_id(app):
    """One bookable vehicle with both a daily and an hourly rate."""
    with app.app_context():
        db = get_session()
        vehicle = Vehicle(
            plate_number="XYZ 9999",
            brand="Mitsubishi",
            model="Mirage",
            year=2022,
            vehicle_type="Sedan",
            status="AVAILABLE",
            seats=5,
            transmission="Automatic",
            fuel_type="Gasoline",
            daily_rate=Decimal("1300.00"),
            hourly_rate=Decimal("200.00"),
            date_acquired=date(2022, 1, 1),
        )
        db.add(vehicle)
        db.commit()
        return vehicle.id


def test_api_quote_prices_a_window_for_an_anonymous_visitor(client, vehicle_id):
    response = client.get(
        f"/api/quote?vehicle={vehicle_id}&pickup={JAN10}&return={JAN12}"
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["available"] is True
    assert body["total"] == "2600.00"
    assert body["lines"][0] == ["Base rental", "₱1,300.00 x 2 day(s)", "2600.00"]


def test_api_quote_includes_the_extras_when_asked(client, vehicle_id, app):
    with app.app_context():
        db = get_session()
        rates = RentalRates.current(db)
        rates.additional_driver_fee_per_day = Decimal("250.00")
        rates.insurance_fee_per_day = Decimal("300.00")
        db.commit()

    response = client.get(
        f"/api/quote?vehicle={vehicle_id}&pickup={JAN10}&return={JAN12}"
        "&driver=1&insurance=1"
    )

    assert response.get_json()["total"] == "3700.00"


def test_api_quote_reports_a_conflict_rather_than_a_price(client, vehicle_id, app):
    with app.app_context():
        db = get_session()
        customer = db.query(User).filter_by(username="maria").one()
        db.add(
            Reservation(
                user_id=customer.id,
                vehicle_id=vehicle_id,
                pickup_at=datetime(2026, 1, 10, 9, 0),
                return_at=datetime(2026, 1, 12, 9, 0),
                pickup_location="Main office",
                return_location="Main office",
                daily_rate=Decimal("1300.00"),
                base_amount=Decimal("0.00"),
                additional_fees=Decimal("0.00"),
                total_amount=Decimal("0.00"),
                status="CONFIRMED",
            )
        )
        db.commit()

    body = client.get(
        f"/api/quote?vehicle={vehicle_id}&pickup={JAN10}&return={JAN12}"
    ).get_json()

    assert body["available"] is False
    assert body["reason"] == "conflict"
    assert body["total"] is None
    assert body["message"]


def test_api_quote_rejects_an_unusable_window(client, vehicle_id):
    response = client.get(
        f"/api/quote?vehicle={vehicle_id}&pickup={JAN12}&return={JAN10}"
    )

    assert response.status_code == 400
    assert response.get_json()["message"]


def test_api_quote_404s_on_an_unknown_vehicle(client):
    assert client.get(f"/api/quote?vehicle=9999&pickup={JAN10}&return={JAN12}").status_code == 404


def test_api_quote_404s_on_a_disabled_vehicle(client, vehicle_id, app):
    with app.app_context():
        db = get_session()
        db.get(Vehicle, vehicle_id).is_active = False
        db.commit()

    assert client.get(
        f"/api/quote?vehicle={vehicle_id}&pickup={JAN10}&return={JAN12}"
    ).status_code == 404
