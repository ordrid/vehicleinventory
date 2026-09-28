"""Who may reach which page. One table, three kinds of session."""

from __future__ import annotations

import pytest

PUBLIC_PAGES = ["/", "/vehicles"]
ADMIN_PAGES = ["/admin", "/admin/vehicles", "/admin/vehicles/add", "/admin/rates"]
CUSTOMER_PAGES = ["/my"]


@pytest.mark.parametrize("path", PUBLIC_PAGES)
def test_anonymous_visitors_can_browse_the_storefront(client, path):
    assert client.get(path).status_code == 200


@pytest.mark.parametrize("path", ADMIN_PAGES + CUSTOMER_PAGES)
def test_anonymous_visitors_are_sent_to_login_with_a_next_parameter(client, path):
    response = client.get(path)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    assert "next=" in response.headers["Location"]


@pytest.mark.parametrize("path", ADMIN_PAGES)
def test_a_customer_is_refused_every_admin_page(customer_client, path):
    assert customer_client.get(path).status_code == 403


@pytest.mark.parametrize("path", ADMIN_PAGES)
def test_an_admin_reaches_every_admin_page(admin_client, path):
    assert admin_client.get(path).status_code == 200


@pytest.mark.parametrize("path", CUSTOMER_PAGES)
def test_an_admin_is_refused_the_customer_portal(admin_client, path):
    assert admin_client.get(path).status_code == 403


@pytest.mark.parametrize("path", CUSTOMER_PAGES)
def test_a_customer_reaches_their_own_portal(customer_client, path):
    assert customer_client.get(path).status_code == 200


@pytest.mark.parametrize("path", ADMIN_PAGES + CUSTOMER_PAGES)
def test_no_admin_or_portal_page_answers_with_a_trailing_slash_redirect(admin_client, path):
    """A blueprint prefix plus @bp.route("/") registers "/admin/", not "/admin".

    Werkzeug then answers 308 for "/admin", which silently breaks every link and
    every test that expects 200. Empty rules avoid it; this locks that in.
    """
    assert admin_client.get(path).status_code != 308


def test_guest_mode_is_gone(client):
    assert client.post("/guest").status_code == 404


def test_an_admin_reaches_an_admin_guarded_page(admin_client):
    assert admin_client.get("/admin/vehicles").status_code == 200


def test_a_customer_is_refused_an_admin_guarded_page(customer_client):
    assert customer_client.get("/admin/vehicles").status_code == 403


def test_an_anonymous_visitor_is_redirected_with_a_next_parameter(client):
    response = client.get("/admin/vehicles")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    assert "next=" in response.headers["Location"]
