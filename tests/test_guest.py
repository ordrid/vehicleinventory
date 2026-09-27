"""Guest mode: a session with no account behind it that can read but not change."""

from __future__ import annotations

import pytest

READ_ONLY_PAGES = [
    "/",
    "/vehicles",
    "/search",
    "/reports",
    "/reports/export.csv",
]

# The pages that change data. GET is enough to prove the guard, because every
# one of these renders a form on GET.
WRITE_PAGES = [
    "/vehicles/add",
    "/vehicles/{id}/edit",
    "/vehicles/{id}/delete",
]


def test_guest_button_starts_a_read_only_session(client):
    """Posting to /guest lands on the dashboard without signing anyone in."""
    response = client.post("/guest", follow_redirects=True)

    assert response.status_code == 200
    assert b"read-only mode" in response.data


def test_login_page_offers_guest_access(client):
    """The login page shows the Continue as guest button."""
    response = client.get("/login")

    assert b"Continue as guest" in response.data


@pytest.mark.parametrize("path", READ_ONLY_PAGES)
def test_guest_can_read_every_view_page(guest_client, sample_vehicle, path):
    """Every read-only page answers 200 for a guest."""
    assert guest_client.get(path).status_code == 200


def test_guest_can_open_a_vehicle_detail_page(guest_client, sample_vehicle):
    """The detail page shows the full record, including fields the table omits."""
    response = guest_client.get(f"/vehicles/{sample_vehicle}")

    assert response.status_code == 200
    assert b"ABC 1234" in response.data
    assert b"15 Mar 2021" in response.data


@pytest.mark.parametrize("path", WRITE_PAGES)
def test_guest_is_refused_on_write_pages(guest_client, sample_vehicle, path):
    """Asking for a page that changes data gives a 403, not a form."""
    response = guest_client.get(path.format(id=sample_vehicle))

    assert response.status_code == 403
    assert b"browsing as a guest" in response.data


def test_guest_cannot_post_a_delete(guest_client, sample_vehicle, client):
    """A guest posting the delete form is refused and the vehicle survives."""
    response = guest_client.post(f"/vehicles/{sample_vehicle}/delete")

    assert response.status_code == 403
    assert guest_client.get(f"/vehicles/{sample_vehicle}").status_code == 200


def test_guest_sees_no_edit_or_delete_links(guest_client, sample_vehicle):
    """The vehicle table offers a guest View only."""
    body = guest_client.get("/vehicles").data

    assert b"View" in body
    assert f"/vehicles/{sample_vehicle}/edit".encode() not in body
    assert f"/vehicles/{sample_vehicle}/delete".encode() not in body
    assert b"Add Vehicle" not in body


def test_signed_in_user_still_sees_edit_and_delete(auth_client, sample_vehicle):
    """The same table keeps every action for a signed-in user."""
    body = auth_client.get("/vehicles").data

    assert f"/vehicles/{sample_vehicle}/edit".encode() in body
    assert f"/vehicles/{sample_vehicle}/delete".encode() in body
    assert b"Add Vehicle" in body


def test_leaving_guest_mode_returns_to_anonymous(guest_client):
    """Exit guest clears the session, so the next page redirects to login."""
    guest_client.post("/logout")

    response = guest_client.get("/vehicles")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_guest_mode_does_not_survive_a_login(guest_client):
    """Signing in from a guest session replaces it with a real account."""
    guest_client.post("/login", data={"username": "admin", "password": "secret123"})

    body = guest_client.get("/vehicles").data
    assert b"Add Vehicle" in body
    assert b"read-only mode" not in body
