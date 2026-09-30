"""The three admin actions that close the loop: confirm, start, return."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from rental.clock import now
from rental.db import get_session
from rental.models import Rental, RentalRates, Reservation, User, Vehicle


@pytest.fixture
def vehicle_id(app):
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
            date_acquired=date(2022, 1, 1),
        )
        db.add(vehicle)
        db.commit()
        return vehicle.id


def add_reservation(app, vehicle_id, *, status="PENDING", starts_in_days=1, days=2):
    with app.app_context():
        db = get_session()
        user = db.query(User).filter_by(username="maria").one()
        start = now() + timedelta(days=starts_in_days)
        reservation = Reservation(
            user_id=user.id,
            vehicle_id=vehicle_id,
            pickup_at=start,
            return_at=start + timedelta(days=days),
            pickup_location="Main office",
            return_location="Main office",
            rental_hours=days * 24,
            rental_days=days,
            daily_rate=Decimal("1300.00"),
            base_amount=Decimal("1300.00") * days,
            additional_fees=Decimal("0.00"),
            total_amount=Decimal("1300.00") * days,
            status=status,
        )
        db.add(reservation)
        db.flush()
        reservation.assign_number()
        db.commit()
        return reservation.id


def test_the_queue_shows_an_empty_state_when_nothing_is_waiting(admin_client):
    assert "queue is clear" in admin_client.get("/admin/reservations").get_data(as_text=True).lower()


def test_the_queue_lists_a_pending_request(admin_client, app, vehicle_id):
    add_reservation(app, vehicle_id)

    body = admin_client.get("/admin/reservations").get_data(as_text=True)

    assert "RES-00001" in body
    assert "Maria Santos" in body
    assert "Confirm" in body
    assert "Reject" in body


def test_confirm_moves_the_reservation_and_reserves_the_vehicle(admin_client, app, vehicle_id):
    reservation_id = add_reservation(app, vehicle_id)

    assert admin_client.post(f"/admin/reservations/{reservation_id}/confirm").status_code == 302
    with app.app_context():
        db = get_session()
        assert db.get(Reservation, reservation_id).status == "CONFIRMED"
        assert db.get(Vehicle, vehicle_id).status == "RESERVED"


def test_reject_declines_the_request_and_frees_the_vehicle(admin_client, app, vehicle_id):
    reservation_id = add_reservation(app, vehicle_id)

    assert admin_client.post(f"/admin/reservations/{reservation_id}/reject").status_code == 302
    with app.app_context():
        db = get_session()
        assert db.get(Reservation, reservation_id).status == "REJECTED"
        assert db.get(Vehicle, vehicle_id).status == "AVAILABLE"


def test_confirming_twice_is_a_message_not_a_500(admin_client, app, vehicle_id):
    reservation_id = add_reservation(app, vehicle_id, status="CONFIRMED")

    response = admin_client.post(
        f"/admin/reservations/{reservation_id}/confirm", follow_redirects=True
    )

    assert response.status_code == 200
    assert "cannot" in response.get_data(as_text=True).lower()
    with app.app_context():
        assert get_session().get(Reservation, reservation_id).status == "CONFIRMED"


def test_a_customer_is_refused_the_queue(customer_client):
    assert customer_client.get("/admin/reservations").status_code == 403


def test_a_customer_cannot_confirm_a_reservation(customer_client, app, vehicle_id):
    reservation_id = add_reservation(app, vehicle_id)

    assert customer_client.post(f"/admin/reservations/{reservation_id}/confirm").status_code == 403
    with app.app_context():
        assert get_session().get(Reservation, reservation_id).status == "PENDING"


def test_confirm_404s_on_a_reservation_that_does_not_exist(admin_client):
    assert admin_client.post("/admin/reservations/9999/confirm").status_code == 404
