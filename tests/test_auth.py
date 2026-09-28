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
    assert b"Signed in successfully." in response.data


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


def test_logout_clears_the_session(admin_client):
    response = admin_client.post("/logout", follow_redirects=True)
    assert b"You have been logged out." in response.data
    assert admin_client.get("/vehicles").status_code == 302


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


def test_expired_csrf_token_shows_a_friendly_message(app):
    """A stale tab should get a flash message, not Flask-WTF's bare 400 page."""
    app.config["WTF_CSRF_ENABLED"] = True
    client = app.test_client()

    response = client.post("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"Your session expired." in response.data


def test_guest_mode_is_gone(client):
    assert client.post("/guest").status_code == 404


def test_an_admin_reaches_an_admin_guarded_page(admin_client):
    assert admin_client.get("/vehicles").status_code == 200


def test_a_customer_is_refused_an_admin_guarded_page(customer_client):
    assert customer_client.get("/vehicles").status_code == 403


def test_an_anonymous_visitor_is_redirected_with_a_next_parameter(client):
    response = client.get("/vehicles")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    assert "next=" in response.headers["Location"]


def test_signup_creates_a_customer(app, client):
    client.post(
        "/signup",
        data={
            "username": "newbie",
            "email": "newbie@example.com",
            "full_name": "New Customer",
            "phone": "0917 000 9999",
            "password": "password123",
            "confirm_password": "password123",
        },
    )
    with app.app_context():
        from rental.auth import find_user_by_username

        user = find_user_by_username("newbie")
        assert user.role == "customer"
        assert user.full_name == "New Customer"


def test_a_disabled_account_cannot_sign_in(app, client):
    with app.app_context():
        from rental.auth import find_user_by_username
        from rental.db import get_session

        db = get_session()
        find_user_by_username("maria").is_active = False
        db.commit()

    response = client.post(
        "/login", data={"username": "maria", "password": "secret123"}, follow_redirects=True
    )
    assert b"has been disabled" in response.data


def test_forgot_password_records_the_request(app, client):
    response = client.post(
        "/forgot-password", data={"email": "maria@example.com"}, follow_redirects=True
    )
    assert b"asked the office" in response.data

    with app.app_context():
        from rental.auth import find_user_by_email

        assert find_user_by_email("maria@example.com").reset_requested_at is not None


def test_forgot_password_says_the_same_thing_for_an_unknown_address(client):
    response = client.post(
        "/forgot-password", data={"email": "nobody@example.com"}, follow_redirects=True
    )
    assert b"asked the office" in response.data


def test_a_temporary_password_forces_a_change_before_anything_else(app, admin_client):
    # /my does not exist until Task 11. The before_request gate is
    # route-independent, so this asserts the same behaviour against
    # /vehicles, an admin-guarded route that exists today.
    with app.app_context():
        from rental.auth import find_user_by_username
        from rental.db import get_session

        db = get_session()
        find_user_by_username("admin").must_change_password = True
        db.commit()

    response = admin_client.get("/vehicles")
    assert response.status_code == 302
    assert "/change-password" in response.headers["Location"]


def test_changing_the_password_clears_the_flag_and_lets_you_back_in(app, admin_client):
    with app.app_context():
        from rental.auth import find_user_by_username
        from rental.db import get_session

        db = get_session()
        find_user_by_username("admin").must_change_password = True
        db.commit()

    admin_client.post(
        "/change-password",
        data={
            "current_password": "secret123",
            "password": "brandnew123",
            "confirm_password": "brandnew123",
        },
    )

    with app.app_context():
        from rental.auth import find_user_by_username

        user = find_user_by_username("admin")
        assert user.must_change_password is False
        assert user.check_password("brandnew123")

    assert admin_client.get("/vehicles").status_code == 200


def test_a_wrong_current_password_is_refused(customer_client):
    response = customer_client.post(
        "/change-password",
        data={
            "current_password": "wrong-password",
            "password": "brandnew123",
            "confirm_password": "brandnew123",
        },
    )
    assert b"current password is not correct" in response.data
