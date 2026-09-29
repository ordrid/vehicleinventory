"""What a rental costs. Pure arithmetic -- no app, no database, no clock."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from rental.domain.pricing import Duration, duration_between, money

PICKUP = datetime(2026, 10, 1, 9, 0)


def at(**kwargs) -> datetime:
    """The return time, offset from a fixed pickup."""
    return PICKUP + timedelta(**kwargs)


def test_money_quantises_to_two_places():
    assert money(Decimal("1500")) == Decimal("1500.00")
    assert money("1500.4") == Decimal("1500.40")


def test_money_rounds_half_up():
    """Half-up, not banker's rounding: a customer expects 0.125 to become 0.13."""
    assert money(Decimal("0.125")) == Decimal("0.13")
    assert money(Decimal("0.135")) == Decimal("0.14")


def test_the_requirements_worked_example_is_three_whole_days():
    d = duration_between(PICKUP, at(days=3))
    assert d == Duration(hours=72, full_days=3, extra_hours=0, billable_days=3)


def test_a_part_hour_rounds_up():
    """A rental is billed for the hour it begins."""
    assert duration_between(PICKUP, at(minutes=1)).hours == 1
    assert duration_between(PICKUP, at(hours=2, minutes=1)).hours == 3


def test_the_day_boundary():
    assert duration_between(PICKUP, at(hours=23)).full_days == 0
    assert duration_between(PICKUP, at(hours=24)).full_days == 1
    assert duration_between(PICKUP, at(hours=25)).full_days == 1
    assert duration_between(PICKUP, at(hours=25)).extra_hours == 1


def test_billable_days_rounds_a_part_day_up():
    """Per-day extras charge whole days even when the base is billed hourly."""
    assert duration_between(PICKUP, at(hours=1)).billable_days == 1
    assert duration_between(PICKUP, at(hours=24)).billable_days == 1
    assert duration_between(PICKUP, at(hours=25)).billable_days == 2


def test_a_minimum_of_one_hour_is_charged():
    assert duration_between(PICKUP, at(seconds=30)).hours == 1


def test_a_zero_or_reversed_span_is_refused():
    """A validation failure the caller should have caught, not a free rental."""
    with pytest.raises(ValueError):
        duration_between(PICKUP, PICKUP)
    with pytest.raises(ValueError):
        duration_between(PICKUP, at(hours=-1))
