"""Which status changes are legal, and what each operation changes.

Requirement 18 lists five things that must happen when a vehicle is returned,
across three tables. Returning every resulting status from one function is what
stops a route performing four of them.
"""

from __future__ import annotations

import pytest

from rental.domain.lifecycle import (
    RENTAL_TRANSITIONS,
    RESERVATION_TRANSITIONS,
    StateChange,
    TransitionError,
    assert_transition,
    can_transition,
    cancel_reservation,
    complete_rental,
    confirm_reservation,
    reject_reservation,
    start_rental,
)


# -- the transition tables --------------------------------------------------

@pytest.mark.parametrize(
    "current,target",
    [
        ("PENDING", "CONFIRMED"),
        ("PENDING", "REJECTED"),
        ("PENDING", "CANCELLED"),
        ("CONFIRMED", "CANCELLED"),
        ("CONFIRMED", "COMPLETED"),
    ],
)
def test_every_legal_reservation_transition(current, target):
    assert can_transition(RESERVATION_TRANSITIONS, current, target) is True


@pytest.mark.parametrize(
    "current,target",
    [
        ("PENDING", "COMPLETED"),   # cannot finish what was never confirmed
        ("CONFIRMED", "PENDING"),   # no going back
        ("CONFIRMED", "REJECTED"),  # reject is for pending requests only
        ("CANCELLED", "CONFIRMED"),
        ("REJECTED", "CONFIRMED"),
        ("COMPLETED", "CANCELLED"),
    ],
)
def test_every_illegal_reservation_transition(current, target):
    assert can_transition(RESERVATION_TRANSITIONS, current, target) is False
    with pytest.raises(TransitionError):
        assert_transition(RESERVATION_TRANSITIONS, current, target)


@pytest.mark.parametrize("status", ["CANCELLED", "REJECTED", "COMPLETED"])
def test_terminal_reservation_states_go_nowhere(status):
    assert RESERVATION_TRANSITIONS[status] == set()


def test_the_rental_table():
    assert can_transition(RENTAL_TRANSITIONS, "ACTIVE", "COMPLETED") is True
    assert can_transition(RENTAL_TRANSITIONS, "COMPLETED", "ACTIVE") is False
    assert RENTAL_TRANSITIONS["COMPLETED"] == set()


def test_an_unknown_status_is_a_bug_not_a_refusal():
    """KeyError, not False: a typo must surface rather than silently deny."""
    with pytest.raises(KeyError):
        can_transition(RESERVATION_TRANSITIONS, "PENDIGN", "CONFIRMED")


def test_an_unknown_target_is_simply_illegal():
    assert can_transition(RESERVATION_TRANSITIONS, "PENDING", "NONSENSE") is False


# -- the operations ---------------------------------------------------------

def test_confirming_reserves_the_vehicle():
    assert confirm_reservation("PENDING") == StateChange(
        reservation_status="CONFIRMED", rental_status=None, vehicle_status="RESERVED",
    )


def test_rejecting_frees_the_vehicle():
    assert reject_reservation("PENDING") == StateChange(
        reservation_status="REJECTED", rental_status=None, vehicle_status="AVAILABLE",
    )


def test_cancelling_frees_the_vehicle():
    assert cancel_reservation("CONFIRMED") == StateChange(
        reservation_status="CANCELLED", rental_status=None, vehicle_status="AVAILABLE",
    )


def test_starting_a_rental_marks_the_vehicle_rented():
    assert start_rental("CONFIRMED") == StateChange(
        reservation_status="CONFIRMED", rental_status="ACTIVE", vehicle_status="RENTED",
    )


def test_completing_a_rental_closes_all_three():
    """The five-part return of requirement 18, as one value."""
    assert complete_rental("CONFIRMED", "ACTIVE") == StateChange(
        reservation_status="COMPLETED", rental_status="COMPLETED", vehicle_status="AVAILABLE",
    )


# -- the guards -------------------------------------------------------------

def test_a_rental_cannot_start_from_an_unconfirmed_reservation():
    with pytest.raises(TransitionError):
        start_rental("PENDING")


def test_a_rental_cannot_start_from_a_cancelled_reservation():
    with pytest.raises(TransitionError):
        start_rental("CANCELLED")


def test_a_completed_rental_cannot_be_completed_again():
    with pytest.raises(TransitionError):
        complete_rental("CONFIRMED", "COMPLETED")


def test_confirming_twice_is_refused():
    with pytest.raises(TransitionError):
        confirm_reservation("CONFIRMED")


def test_rejecting_a_confirmed_reservation_is_refused():
    """Once confirmed it is cancelled, not rejected -- they mean different things."""
    with pytest.raises(TransitionError):
        reject_reservation("CONFIRMED")
