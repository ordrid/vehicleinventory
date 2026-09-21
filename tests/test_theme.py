"""The light / dark theme switch, which is stored in the session and uses no JavaScript."""

from __future__ import annotations


def test_default_has_no_data_theme_so_it_follows_the_system(client):
    """With no choice made, the html tag carries no data-theme attribute."""
    response = client.get("/login")
    assert b"data-theme" not in response.data


def test_choosing_dark_renders_the_forest_theme(client):
    response = client.post("/theme", data={"theme": "dark", "next": "/login"}, follow_redirects=True)
    assert b'data-theme="forest"' in response.data


def test_choosing_light_renders_the_emerald_theme(client):
    response = client.post(
        "/theme", data={"theme": "light", "next": "/login"}, follow_redirects=True
    )
    assert b'data-theme="emerald"' in response.data


def test_choice_persists_across_pages(auth_client):
    auth_client.post("/theme", data={"theme": "dark", "next": "/"})
    for path in ["/", "/vehicles", "/search", "/reports"]:
        assert b'data-theme="forest"' in auth_client.get(path).data


def test_choosing_auto_clears_the_attribute_again(client):
    client.post("/theme", data={"theme": "dark", "next": "/login"})
    response = client.post(
        "/theme", data={"theme": "auto", "next": "/login"}, follow_redirects=True
    )
    assert b"data-theme" not in response.data


def test_an_unknown_theme_value_falls_back_to_auto(client):
    response = client.post(
        "/theme", data={"theme": "<script>", "next": "/login"}, follow_redirects=True
    )
    assert b"data-theme" not in response.data


def test_theme_survives_logging_in_and_out(client):
    client.post("/theme", data={"theme": "dark", "next": "/login"})

    logged_in = client.post(
        "/login", data={"username": "admin", "password": "secret123"}, follow_redirects=True
    )
    assert b'data-theme="forest"' in logged_in.data

    logged_out = client.post("/logout", follow_redirects=True)
    assert b'data-theme="forest"' in logged_out.data


def test_theme_switch_redirects_back_to_the_page_you_came_from(auth_client):
    response = auth_client.post("/theme", data={"theme": "dark", "next": "/search?q=toyota"})
    assert response.status_code == 302
    assert response.headers["Location"] == "/search?q=toyota"


def test_theme_switch_ignores_an_off_site_redirect(auth_client):
    response = auth_client.post("/theme", data={"theme": "dark", "next": "//evil.example.com"})
    assert response.headers["Location"] == "/"


def test_expired_csrf_token_shows_a_friendly_message(app):
    """A stale tab should get a flash message, not Flask-WTF's bare 400 page."""
    app.config["WTF_CSRF_ENABLED"] = True
    client = app.test_client()

    response = client.post("/theme", data={"theme": "dark"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Your session expired." in response.data
