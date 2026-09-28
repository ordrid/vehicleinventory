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


def test_rental_rates_current_creates_the_single_row(app):
    from rental.db import get_session
    from rental.models import RentalRates

    with app.app_context():
        db = get_session()
        rates = RentalRates.current(db)
        assert rates.id == 1
        assert rates.additional_driver_fee_per_day == Decimal("500.00")
        assert rates.insurance_fee_per_day == Decimal("300.00")
        assert rates.late_fee_per_day == Decimal("800.00")


def test_rental_rates_current_reuses_the_row_and_keeps_edits(app):
    from rental.db import get_session
    from rental.models import RentalRates

    with app.app_context():
        db = get_session()
        RentalRates.current(db).insurance_fee_per_day = Decimal("350.00")
        db.commit()

        again = RentalRates.current(db)
        assert again.id == 1
        assert again.insurance_fee_per_day == Decimal("350.00")
        assert db.query(RentalRates).count() == 1
