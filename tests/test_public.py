"""The public storefront: the landing page, the browse grid and vehicle detail."""

from __future__ import annotations


def test_the_landing_page_sells_the_rental_system(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Rent the Right Vehicle" in response.data
    assert b"Browse Vehicles" in response.data
    assert b"Automatic Calculation" in response.data


def test_the_landing_page_shows_real_vehicles(client, sample_vehicle):
    response = client.get("/")
    assert b"Toyota Hilux" in response.data


def test_the_landing_page_counts_what_is_actually_available(client, sample_vehicle):
    assert b"1 vehicle" in client.get("/").data


def test_browse_lists_active_vehicles_with_their_rate(client, sample_vehicle):
    response = client.get("/vehicles")
    assert response.status_code == 200
    assert b"Toyota Hilux" in response.data
    assert "₱2,200".encode() in response.data


def test_browse_filters_by_type(client, sample_vehicle):
    assert b"Toyota Hilux" in client.get("/vehicles?type=Pickup").data
    assert b"Toyota Hilux" not in client.get("/vehicles?type=Sedan").data


def test_browse_filters_by_transmission_and_seats(client, sample_vehicle):
    assert b"Toyota Hilux" in client.get("/vehicles?transmission=Automatic&seats=5").data
    assert b"Toyota Hilux" not in client.get("/vehicles?transmission=Manual").data
    assert b"Toyota Hilux" not in client.get("/vehicles?seats=7").data


def test_browse_filters_by_rate_range(client, sample_vehicle):
    assert b"Toyota Hilux" in client.get("/vehicles?min_rate=1000&max_rate=3000").data
    assert b"Toyota Hilux" not in client.get("/vehicles?max_rate=1000").data


def test_a_disabled_vehicle_leaves_the_storefront(app, client, sample_vehicle):
    from rental.db import get_session
    from rental.models import Vehicle

    with app.app_context():
        db = get_session()
        db.get(Vehicle, sample_vehicle).is_active = False
        db.commit()

    assert b"Toyota Hilux" not in client.get("/vehicles").data


def test_browse_has_an_empty_state_that_offers_a_way_out(client):
    response = client.get("/vehicles?type=Motorcycle")
    assert b"No vehicles match" in response.data
    assert b"Show all vehicles" in response.data
