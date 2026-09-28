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
