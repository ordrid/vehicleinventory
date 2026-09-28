"""Adding, viewing, searching, editing and deleting vehicles."""

from __future__ import annotations

from decimal import Decimal

from rental.db import get_session
from rental.models import Vehicle

NEW_VEHICLE = {
    "plate_number": "  new 9999 ",
    "brand": "Nissan",
    "model": "Navara",
    "year": "2022",
    "vehicle_type": "Pickup",
    "color": "Grey",
    "status": "AVAILABLE",
    "seats": "5",
    "transmission": "Automatic",
    "fuel_type": "Gasoline",
    "daily_rate": "1500.00",
    "hourly_rate": "",
    "image_url": "",
    "date_acquired": "2022-04-01",
    "description": "Bought new.",
}


def test_dashboard_shows_totals(admin_client, sample_vehicle):
    response = admin_client.get("/admin")
    assert response.status_code == 200
    assert b"Rental Management Dashboard" in response.data
    # One vehicle, and it is AVAILABLE, so both those tiles must read 1.
    assert response.data.count(b">1</p>") == 2
    assert b"AVAILABLE" in response.data


def test_add_vehicle_saves_and_normalises_the_plate(app, admin_client):
    response = admin_client.post("/admin/vehicles/add", data=NEW_VEHICLE, follow_redirects=True)
    assert response.status_code == 200
    assert b"Vehicle NEW 9999 was added." in response.data

    with app.app_context():
        vehicle = get_session().query(Vehicle).filter_by(plate_number="NEW 9999").one()
        assert vehicle.brand == "Nissan"
        assert vehicle.year == 2022


def test_add_vehicle_rejects_a_duplicate_plate(admin_client, sample_vehicle):
    data = dict(NEW_VEHICLE, plate_number="ABC 1234")
    response = admin_client.post("/admin/vehicles/add", data=data)
    assert response.status_code == 200
    assert b"already exists" in response.data


def test_add_vehicle_rejects_an_out_of_range_year(admin_client):
    data = dict(NEW_VEHICLE, year="1800")
    response = admin_client.post("/admin/vehicles/add", data=data)
    assert b"Year must be between" in response.data


def test_view_vehicles_lists_the_vehicle(admin_client, sample_vehicle):
    response = admin_client.get("/admin/vehicles")
    assert response.status_code == 200
    assert b"ABC 1234" in response.data
    assert b"Hilux" in response.data


def test_view_vehicles_paginates_at_ten_per_page(app, admin_client):
    with app.app_context():
        db = get_session()
        for number in range(12):
            db.add(
                Vehicle(
                    plate_number=f"PAG {number:04d}",
                    brand="Toyota",
                    model="Vios",
                    year=2020,
                    vehicle_type="Sedan",
                    status="AVAILABLE",
                    daily_rate=Decimal("1500.00"),
                )
            )
        db.commit()

    first_page = admin_client.get("/admin/vehicles?sort=plate&dir=asc")
    assert first_page.data.count(b"PAG ") == 10
    assert b"PAG 0010" not in first_page.data

    second_page = admin_client.get("/admin/vehicles?sort=plate&dir=asc&page=2")
    assert b"PAG 0010" in second_page.data


def test_view_vehicles_sorts_by_year(app, admin_client, sample_vehicle):
    with app.app_context():
        db = get_session()
        db.add(
            Vehicle(
                plate_number="OLD 0001",
                brand="Honda",
                model="Civic",
                year=1999,
                vehicle_type="Sedan",
                status="MAINTENANCE",
                daily_rate=Decimal("1200.00"),
            )
        )
        db.commit()

    ascending = admin_client.get("/admin/vehicles?sort=year&dir=asc").data
    assert ascending.index(b"OLD 0001") < ascending.index(b"ABC 1234")

    descending = admin_client.get("/admin/vehicles?sort=year&dir=desc").data
    assert descending.index(b"ABC 1234") < descending.index(b"OLD 0001")


def test_search_matches_case_insensitive_partial_text(admin_client, sample_vehicle):
    assert b"ABC 1234" in admin_client.get("/admin/vehicles/search?q=toyo").data
    assert b"ABC 1234" in admin_client.get("/admin/vehicles/search?q=hilu").data
    assert b"ABC 1234" in admin_client.get("/admin/vehicles/search?q=abc").data


def test_search_with_no_match_says_so(admin_client, sample_vehicle):
    response = admin_client.get("/admin/vehicles/search?q=zzzzz")
    assert b"No vehicles matched your search." in response.data


def test_search_filters_by_status_and_type(admin_client, sample_vehicle):
    assert b"ABC 1234" in admin_client.get("/admin/vehicles/search?status=AVAILABLE").data
    assert b"ABC 1234" not in admin_client.get("/admin/vehicles/search?status=MAINTENANCE").data
    assert b"ABC 1234" in admin_client.get("/admin/vehicles/search?type=Pickup").data
    assert b"ABC 1234" not in admin_client.get("/admin/vehicles/search?type=Sedan").data


def test_edit_vehicle_prefills_and_saves(app, admin_client, sample_vehicle):
    page = admin_client.get(f"/admin/vehicles/{sample_vehicle}/edit")
    assert page.status_code == 200
    assert b"ABC 1234" in page.data

    data = dict(NEW_VEHICLE, plate_number="ABC 1234", status="MAINTENANCE", color="Blue")
    response = admin_client.post(
        f"/admin/vehicles/{sample_vehicle}/edit", data=data, follow_redirects=True
    )
    assert b"Vehicle ABC 1234 was updated." in response.data

    with app.app_context():
        vehicle = get_session().get(Vehicle, sample_vehicle)
        assert vehicle.status == "MAINTENANCE"
        assert vehicle.color == "Blue"


def test_edit_vehicle_rejects_a_plate_used_by_another_vehicle(app, admin_client, sample_vehicle):
    with app.app_context():
        db = get_session()
        db.add(
            Vehicle(
                plate_number="DUP 0001",
                brand="Ford",
                model="Ranger",
                year=2020,
                vehicle_type="Pickup",
                status="AVAILABLE",
                daily_rate=Decimal("1800.00"),
            )
        )
        db.commit()

    data = dict(NEW_VEHICLE, plate_number="DUP 0001")
    response = admin_client.post(f"/admin/vehicles/{sample_vehicle}/edit", data=data)
    assert b"Another vehicle already uses plate DUP 0001." in response.data


def test_delete_shows_a_confirmation_page_and_does_not_delete_on_get(
    app, admin_client, sample_vehicle
):
    response = admin_client.get(f"/admin/vehicles/{sample_vehicle}/delete")
    assert response.status_code == 200
    assert b"This cannot be undone." in response.data

    with app.app_context():
        assert get_session().get(Vehicle, sample_vehicle) is not None


def test_delete_removes_the_vehicle_on_post(app, admin_client, sample_vehicle):
    response = admin_client.post(f"/admin/vehicles/{sample_vehicle}/delete", follow_redirects=True)
    assert b"Vehicle ABC 1234 was deleted." in response.data

    with app.app_context():
        assert get_session().get(Vehicle, sample_vehicle) is None


def test_missing_vehicle_returns_the_custom_404_page(admin_client):
    response = admin_client.get("/admin/vehicles/999999/edit")
    assert response.status_code == 404
    assert b"Page not found" in response.data


def test_the_fleet_table_shows_the_daily_rate(admin_client, sample_vehicle):
    assert "₱2,200.00".encode() in admin_client.get("/admin/vehicles").data


def test_adding_a_vehicle_without_a_rate_is_refused(admin_client):
    response = admin_client.post("/admin/vehicles/add", data=dict(NEW_VEHICLE, daily_rate=""))
    assert response.status_code == 200
    assert b"Daily rate is required." in response.data


def test_a_negative_rate_is_refused(admin_client):
    response = admin_client.post("/admin/vehicles/add", data=dict(NEW_VEHICLE, daily_rate="-50"))
    assert b"cannot be negative" in response.data


def test_toggle_active_disables_and_re_enables_a_vehicle(app, admin_client, sample_vehicle):
    from rental.db import get_session
    from rental.models import Vehicle

    admin_client.post(f"/admin/vehicles/{sample_vehicle}/toggle-active")
    with app.app_context():
        assert get_session().get(Vehicle, sample_vehicle).is_active is False

    admin_client.post(f"/admin/vehicles/{sample_vehicle}/toggle-active")
    with app.app_context():
        assert get_session().get(Vehicle, sample_vehicle).is_active is True


def test_toggle_active_refuses_a_get(admin_client, sample_vehicle):
    assert admin_client.get(f"/admin/vehicles/{sample_vehicle}/toggle-active").status_code == 405


def test_a_customer_cannot_disable_a_vehicle(customer_client, sample_vehicle):
    assert customer_client.post(
        f"/admin/vehicles/{sample_vehicle}/toggle-active"
    ).status_code == 403


def test_an_admin_still_sees_every_action_control(admin_client, sample_vehicle):
    """Guard against a role flag silently disappearing from the templates.

    Jinja renders an undefined name as falsy rather than raising, so renaming or
    dropping the flag these templates test would hide every action control from
    every admin without a single test failing. Task 6 shipped exactly that bug
    (`is_editor` outlived the context processor that defined it) and it was
    caught by eye, not by the suite -- because the one test covering it had been
    deleted along with guest mode. This is that test, restored.
    """
    listing = admin_client.get("/admin/vehicles").get_data(as_text=True)
    assert "Add Vehicle" in listing
    assert f"/admin/vehicles/{sample_vehicle}/edit" in listing
    assert f"/admin/vehicles/{sample_vehicle}/delete" in listing

    detail = admin_client.get(f"/admin/vehicles/{sample_vehicle}").get_data(as_text=True)
    assert f"/admin/vehicles/{sample_vehicle}/edit" in detail
    assert f"/admin/vehicles/{sample_vehicle}/delete" in detail
    assert f"/admin/vehicles/{sample_vehicle}/toggle-active" in detail
