"""The reports page and the CSV export."""

from __future__ import annotations

import csv
import io


def test_reports_page_shows_the_three_summary_tables(auth_client, sample_vehicle):
    response = auth_client.get("/reports")
    assert response.status_code == 200
    assert b"Vehicles by status" in response.data
    assert b"Vehicles by type" in response.data
    assert b"Vehicles by year acquired" in response.data
    # The single sample vehicle was acquired in 2021.
    assert b"2021" in response.data


def test_reports_page_requires_login(client):
    assert client.get("/reports").status_code == 302


def test_csv_export_returns_a_downloadable_file(auth_client, sample_vehicle):
    response = auth_client.get("/reports/export.csv")
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "attachment" in response.headers["Content-Disposition"]

    rows = list(csv.reader(io.StringIO(response.get_data(as_text=True))))
    assert rows[0][1] == "plate_number"
    assert rows[1][1] == "ABC 1234"
    assert rows[1][2] == "Toyota"
