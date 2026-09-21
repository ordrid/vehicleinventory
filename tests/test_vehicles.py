"""Adding, viewing, searching, editing and deleting vehicles."""

from __future__ import annotations

from inventory.db import get_session
from inventory.models import Vehicle

NEW_VEHICLE = {
    "plate_number": "  new 9999 ",
    "make": "Nissan",
    "model": "Navara",
    "year": "2022",
    "vehicle_type": "Pickup",
    "color": "Grey",
    "status": "Available",
    "date_acquired": "2022-04-01",
    "remarks": "Bought new.",
}


def test_dashboard_shows_totals(auth_client, sample_vehicle):
    response = auth_client.get("/")
    assert response.status_code == 200
    assert b"All vehicles" in response.data
    assert b"Available" in response.data


def test_add_vehicle_saves_and_normalises_the_plate(app, auth_client):
    response = auth_client.post("/vehicles/add", data=NEW_VEHICLE, follow_redirects=True)
    assert response.status_code == 200
    assert b"Vehicle NEW 9999 was added." in response.data

    with app.app_context():
        vehicle = get_session().query(Vehicle).filter_by(plate_number="NEW 9999").one()
        assert vehicle.make == "Nissan"
        assert vehicle.year == 2022


def test_add_vehicle_rejects_a_duplicate_plate(auth_client, sample_vehicle):
    data = dict(NEW_VEHICLE, plate_number="ABC 1234")
    response = auth_client.post("/vehicles/add", data=data)
    assert response.status_code == 200
    assert b"already exists" in response.data


def test_add_vehicle_rejects_an_out_of_range_year(auth_client):
    data = dict(NEW_VEHICLE, year="1800")
    response = auth_client.post("/vehicles/add", data=data)
    assert b"Year must be between" in response.data


def test_view_vehicles_lists_the_vehicle(auth_client, sample_vehicle):
    response = auth_client.get("/vehicles")
    assert response.status_code == 200
    assert b"ABC 1234" in response.data
    assert b"Hilux" in response.data


def test_view_vehicles_paginates_at_ten_per_page(app, auth_client):
    with app.app_context():
        db = get_session()
        for number in range(12):
            db.add(
                Vehicle(
                    plate_number=f"PAG {number:04d}",
                    make="Toyota",
                    model="Vios",
                    year=2020,
                    vehicle_type="Sedan",
                    status="Available",
                )
            )
        db.commit()

    first_page = auth_client.get("/vehicles?sort=plate&dir=asc")
    assert first_page.data.count(b"PAG ") == 10
    assert b"PAG 0010" not in first_page.data

    second_page = auth_client.get("/vehicles?sort=plate&dir=asc&page=2")
    assert b"PAG 0010" in second_page.data


def test_view_vehicles_sorts_by_year(app, auth_client, sample_vehicle):
    with app.app_context():
        db = get_session()
        db.add(
            Vehicle(
                plate_number="OLD 0001",
                make="Honda",
                model="Civic",
                year=1999,
                vehicle_type="Sedan",
                status="Retired",
            )
        )
        db.commit()

    ascending = auth_client.get("/vehicles?sort=year&dir=asc").data
    assert ascending.index(b"OLD 0001") < ascending.index(b"ABC 1234")

    descending = auth_client.get("/vehicles?sort=year&dir=desc").data
    assert descending.index(b"ABC 1234") < descending.index(b"OLD 0001")


def test_search_matches_case_insensitive_partial_text(auth_client, sample_vehicle):
    assert b"ABC 1234" in auth_client.get("/search?q=toyo").data
    assert b"ABC 1234" in auth_client.get("/search?q=hilu").data
    assert b"ABC 1234" in auth_client.get("/search?q=abc").data


def test_search_with_no_match_says_so(auth_client, sample_vehicle):
    response = auth_client.get("/search?q=zzzzz")
    assert b"No vehicles matched your search." in response.data


def test_search_filters_by_status_and_type(auth_client, sample_vehicle):
    assert b"ABC 1234" in auth_client.get("/search?status=Available").data
    assert b"ABC 1234" not in auth_client.get("/search?status=Retired").data
    assert b"ABC 1234" in auth_client.get("/search?type=Pickup").data
    assert b"ABC 1234" not in auth_client.get("/search?type=Sedan").data


def test_edit_vehicle_prefills_and_saves(app, auth_client, sample_vehicle):
    page = auth_client.get(f"/vehicles/{sample_vehicle}/edit")
    assert page.status_code == 200
    assert b"ABC 1234" in page.data

    data = dict(NEW_VEHICLE, plate_number="ABC 1234", status="Under Maintenance", color="Blue")
    response = auth_client.post(
        f"/vehicles/{sample_vehicle}/edit", data=data, follow_redirects=True
    )
    assert b"Vehicle ABC 1234 was updated." in response.data

    with app.app_context():
        vehicle = get_session().get(Vehicle, sample_vehicle)
        assert vehicle.status == "Under Maintenance"
        assert vehicle.color == "Blue"


def test_edit_vehicle_rejects_a_plate_used_by_another_vehicle(app, auth_client, sample_vehicle):
    with app.app_context():
        db = get_session()
        db.add(
            Vehicle(
                plate_number="DUP 0001",
                make="Ford",
                model="Ranger",
                year=2020,
                vehicle_type="Pickup",
                status="Available",
            )
        )
        db.commit()

    data = dict(NEW_VEHICLE, plate_number="DUP 0001")
    response = auth_client.post(f"/vehicles/{sample_vehicle}/edit", data=data)
    assert b"Another vehicle already uses plate DUP 0001." in response.data


def test_delete_shows_a_confirmation_page_and_does_not_delete_on_get(
    app, auth_client, sample_vehicle
):
    response = auth_client.get(f"/vehicles/{sample_vehicle}/delete")
    assert response.status_code == 200
    assert b"This cannot be undone." in response.data

    with app.app_context():
        assert get_session().get(Vehicle, sample_vehicle) is not None


def test_delete_removes_the_vehicle_on_post(app, auth_client, sample_vehicle):
    response = auth_client.post(f"/vehicles/{sample_vehicle}/delete", follow_redirects=True)
    assert b"Vehicle ABC 1234 was deleted." in response.data

    with app.app_context():
        assert get_session().get(Vehicle, sample_vehicle) is None


def test_missing_vehicle_returns_the_custom_404_page(auth_client):
    response = auth_client.get("/vehicles/999999/edit")
    assert response.status_code == 404
    assert b"Page not found" in response.data
