"""The customer's own pages. Everything here is scoped to the signed-in user."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from rental.clock import now
from rental.db import get_session
from rental.models import Reservation, User, Vehicle


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


def add_reservation(app, vehicle_id, *, username="maria", status="PENDING", starts_in_days=7):
    """Insert one reservation and return its id."""
    with app.app_context():
        db = get_session()
        user = db.query(User).filter_by(username=username).one()
        start = now() + timedelta(days=starts_in_days)
        reservation = Reservation(
            user_id=user.id,
            vehicle_id=vehicle_id,
            pickup_at=start,
            return_at=start + timedelta(days=2),
            pickup_location="Main office",
            return_location="Main office",
            rental_hours=48,
            rental_days=2,
            daily_rate=Decimal("1300.00"),
            base_amount=Decimal("2600.00"),
            additional_fees=Decimal("0.00"),
            total_amount=Decimal("2600.00"),
            status=status,
        )
        db.add(reservation)
        db.flush()
        reservation.assign_number()
        db.commit()
        return reservation.id


def test_my_reservations_shows_an_empty_state_with_a_way_forward(customer_client):
    body = customer_client.get("/my/reservations").get_data(as_text=True)

    assert "No reservations yet" in body
    assert "Browse Vehicles" in body


def test_my_reservations_lists_the_customers_own_bookings(customer_client, app, vehicle_id):
    add_reservation(app, vehicle_id)

    body = customer_client.get("/my/reservations").get_data(as_text=True)

    assert "RES-00001" in body
    assert "Mirage" in body
    assert "2,600.00" in body


def test_my_reservations_does_not_list_another_customers_booking(customer_client, app, vehicle_id):
    add_reservation(app, vehicle_id, username="admin")

    assert "RES-00001" not in customer_client.get("/my/reservations").get_data(as_text=True)


def test_reservation_detail_shows_the_frozen_quote(customer_client, app, vehicle_id):
    reservation_id = add_reservation(app, vehicle_id)

    body = customer_client.get(f"/my/reservations/{reservation_id}").get_data(as_text=True)

    assert "RES-00001" in body
    assert "2,600.00" in body
    assert "Payment Status" in body
    assert "Pending" in body


def test_reservation_detail_404s_on_another_customers_booking(customer_client, app, vehicle_id):
    reservation_id = add_reservation(app, vehicle_id, username="admin")

    # 404, not 403: a 403 would confirm the record exists.
    assert customer_client.get(f"/my/reservations/{reservation_id}").status_code == 404


def test_reservation_detail_404s_on_a_reservation_that_does_not_exist(customer_client):
    assert customer_client.get("/my/reservations/9999").status_code == 404


def test_cancel_before_pickup_releases_the_vehicle(customer_client, app, vehicle_id):
    reservation_id = add_reservation(app, vehicle_id, status="CONFIRMED")
    with app.app_context():
        db = get_session()
        db.get(Vehicle, vehicle_id).status = "RESERVED"
        db.commit()

    response = customer_client.post(f"/my/reservations/{reservation_id}/cancel")

    assert response.status_code == 302
    with app.app_context():
        db = get_session()
        assert db.get(Reservation, reservation_id).status == "CANCELLED"
        assert db.get(Vehicle, vehicle_id).status == "AVAILABLE"


def test_cancel_is_refused_once_pickup_has_passed(customer_client, app, vehicle_id):
    reservation_id = add_reservation(app, vehicle_id, status="CONFIRMED", starts_in_days=-1)

    response = customer_client.post(
        f"/my/reservations/{reservation_id}/cancel", follow_redirects=True
    )

    assert "contact the office" in response.get_data(as_text=True).lower()
    with app.app_context():
        assert get_session().get(Reservation, reservation_id).status == "CONFIRMED"


def test_the_cancel_button_is_gone_once_pickup_has_passed(customer_client, app, vehicle_id):
    reservation_id = add_reservation(app, vehicle_id, status="CONFIRMED", starts_in_days=-1)

    body = customer_client.get(f"/my/reservations/{reservation_id}").get_data(as_text=True)

    assert "/cancel" not in body
    assert "contact the office" in body.lower()


def test_cancel_404s_on_another_customers_booking(customer_client, app, vehicle_id):
    reservation_id = add_reservation(app, vehicle_id, username="admin")

    assert customer_client.post(f"/my/reservations/{reservation_id}/cancel").status_code == 404


def test_cancelling_an_already_cancelled_booking_is_a_message_not_a_500(
    customer_client, app, vehicle_id
):
    reservation_id = add_reservation(app, vehicle_id, status="CANCELLED")

    response = customer_client.post(
        f"/my/reservations/{reservation_id}/cancel", follow_redirects=True
    )

    assert response.status_code == 200
    assert "cannot" in response.get_data(as_text=True).lower()


def test_an_admin_is_refused_the_customer_pages(admin_client):
    assert admin_client.get("/my/reservations").status_code == 403
