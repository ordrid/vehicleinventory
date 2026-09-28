"""The model layer: vocabularies, defaults and derived properties."""

from __future__ import annotations

from decimal import Decimal

from rental.models import STATUS_BADGES, VEHICLE_STATUSES, VEHICLE_TYPES, Vehicle


def test_vehicle_statuses_are_the_four_rental_states():
    assert VEHICLE_STATUSES == ["AVAILABLE", "RESERVED", "RENTED", "MAINTENANCE"]


def test_every_vehicle_status_has_a_badge_colour():
    assert set(STATUS_BADGES) == set(VEHICLE_STATUSES)


def test_vehicle_types_include_the_rental_body_styles():
    assert "Hatchback" in VEHICLE_TYPES
    assert "MPV" in VEHICLE_TYPES


def test_display_name_reads_as_a_rental_listing():
    vehicle = Vehicle(brand="Toyota", model="Vios", year=2024)
    assert vehicle.display_name == "Toyota Vios 2024"


def test_type_slug_picks_the_silhouette_filename():
    assert Vehicle(vehicle_type="MPV").type_slug == "mpv"
    assert Vehicle(vehicle_type="Sedan").type_slug == "sedan"


def test_daily_only_vehicle_has_no_hourly_rate():
    vehicle = Vehicle(daily_rate=Decimal("1500.00"))
    assert vehicle.hourly_rate is None
