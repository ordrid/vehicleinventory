"""Login and logout, plus the rule that every other page needs a session."""

from __future__ import annotations


def test_login_page_loads(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Username" in response.data


def test_login_with_correct_credentials_reaches_dashboard(client):
    response = client.post(
        "/login", data={"username": "admin", "password": "secret123"}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Dashboard" in response.data
    assert b"Welcome back, admin!" in response.data


def test_login_with_wrong_password_shows_error(client):
    response = client.post(
        "/login", data={"username": "admin", "password": "wrong"}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Invalid username or password." in response.data


def test_login_with_unknown_username_shows_error(client):
    response = client.post(
        "/login", data={"username": "nobody", "password": "secret123"}, follow_redirects=True
    )
    assert b"Invalid username or password." in response.data


def test_protected_page_redirects_anonymous_visitor_to_login(client):
    response = client.get("/vehicles")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_logout_clears_the_session(auth_client):
    response = auth_client.post("/logout", follow_redirects=True)
    assert b"You have been logged out." in response.data
    assert auth_client.get("/vehicles").status_code == 302


def test_custom_500_page_is_shown_when_a_view_raises(app):
    """Register a deliberately broken route and confirm the friendly page is returned.

    The route has to be added before the first request is handled, so this test
    builds its own client rather than using the logged-in fixture.
    """

    @app.route("/boom")
    def boom():
        raise RuntimeError("something broke")

    # Without this Flask re-raises the exception instead of calling the handler.
    app.config["PROPAGATE_EXCEPTIONS"] = False

    response = app.test_client().get("/boom")
    assert response.status_code == 500
    assert b"Something went wrong" in response.data
