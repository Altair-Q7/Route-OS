"""The admin report is the customer's read model, so the two must not drift apart."""
import pytest

from conftest import api, auth_headers, routeos_app
from test_native_trips import trip_body, link_ride, client_headers


@pytest.fixture
def reported(monkeypatch, tmp_path):
    monkeypatch.setattr(routeos_app, "DATABASE_PATH", tmp_path / "reports.db")
    monkeypatch.delenv("ROUTEOS_ERPNEXT_URL", raising=False)
    monkeypatch.delenv("ROUTEOS_ERPNEXT_API_KEY", raising=False)
    monkeypatch.delenv("ROUTEOS_ERPNEXT_API_SECRET", raising=False)
    monkeypatch.setenv("ROUTEOS_CLIENT_API_KEY", "saravana-client-key")
    with api() as client:
        admin = client.post("/api/v1/auth/login", json={"name": "Sreekandan Nair"}).json()
        driver = client.post("/api/v1/auth/login", json={"name": "D.B Cooper"}).json()
        yield client, auth_headers(admin), driver, auth_headers(driver)


def two_shop_trip(client, admin, driver, trip="SAP-TRIP-1"):
    body = {
        "trip": trip,
        "driver_id": driver["id"],
        "vehicle": "KL-07-AX-1234",
        "stops": [
            {"stop_ref": "S1", "customer": "Metro Fresh", "latitude": 9.93, "longitude": 76.27,
             "items": [{"product_name": "Idli Batter", "uom": "packet", "planned_quantity": "5"}]},
            {"stop_ref": "S2", "customer": "City Mart", "latitude": 9.94, "longitude": 76.28,
             "items": [{"product_name": "Idli Batter", "uom": "packet", "planned_quantity": "5"}]},
        ],
    }
    response = client.post("/api/v1/deliveries/trips", headers=admin, json=body)
    assert response.status_code == 201, response.text
    return response.json()


def confirm(client, assignment, headers, stop_ref, quantity, status, reason=""):
    stop = next(item for item in assignment["stops"] if item["id"] == stop_ref)
    body = {"status": status, "reason": reason}
    # Only delivered or partial outcomes carry quantities.
    if status in ("delivered", "partial"):
        body["items"] = [{"id": item["id"], "delivered_quantity": quantity}
                         for item in stop["items"]]
    return client.post(f"/api/v1/deliveries/{assignment['id']}/stops/{stop_ref}", headers=headers, json=body)


def test_the_report_is_admin_only(reported):
    client, admin, driver, headers = reported
    assert client.get("/api/v1/reports/deliveries", headers=admin).status_code == 200
    assert client.get("/api/v1/reports/deliveries", headers=headers).status_code == 403
    assert client.get("/api/v1/reports/deliveries").status_code == 401


def test_an_empty_history_reports_nothing_rather_than_failing(reported):
    client, admin, *_ = reported
    report = client.get("/api/v1/reports/deliveries", headers=admin).json()
    assert report == {"trips": [], "product_totals": [], "shortages": []}


def test_totals_and_shortages_are_reported(reported):
    client, admin, driver, headers = reported
    assignment = two_shop_trip(client, admin, driver)
    link_ride(client, assignment, driver, headers)
    confirm(client, assignment, headers, "S1", "5", "delivered")
    confirm(client, assignment, headers, "S2", "3", "partial", reason="Shop had no storage")

    report = client.get("/api/v1/reports/deliveries", headers=admin).json()
    # Ten packets were planned across two shops; eight were handed over.
    totals = {(item["product_name"], item["uom"]): item for item in report["product_totals"]}
    assert totals[("Idli Batter", "packet")]["planned_quantity"] == "10"
    assert totals[("Idli Batter", "packet")]["delivered_quantity"] == "8"
    assert len(report["shortages"]) == 1
    assert report["shortages"][0]["customer"] == "City Mart"
    assert report["shortages"][0]["reason"] == "Shop had no storage"
    assert report["shortages"][0]["items"][0]["delivered_quantity"] == "3"


def test_a_full_delivery_reports_no_shortage(reported):
    client, admin, driver, headers = reported
    assignment = two_shop_trip(client, admin, driver)
    link_ride(client, assignment, driver, headers)
    confirm(client, assignment, headers, "S1", "5", "delivered")
    confirm(client, assignment, headers, "S2", "5", "delivered")
    report = client.get("/api/v1/reports/deliveries", headers=admin).json()
    assert report["shortages"] == []
    assert report["trips"][0]["status"] == "Delivered"


def test_the_report_shows_exactly_what_the_client_api_returns(reported):
    """Testing the screen here has to be a real check of the customer's contract."""
    client, admin, driver, headers = reported
    assignment = two_shop_trip(client, admin, driver)
    link_ride(client, assignment, driver, headers)
    confirm(client, assignment, headers, "S1", "5", "delivered")
    confirm(client, assignment, headers, "S2", "3", "partial", reason="Shop had no storage")

    report = client.get("/api/v1/reports/deliveries", headers=admin).json()
    customer = client.get("/api/v1/client/deliveries", headers=client_headers()).json()
    assert report["trips"] == customer["trips"]
    # The client's own totals agree with the ones the admin screen shows.
    assert report["product_totals"] == customer["trips"][0]["product_totals"]


def test_a_failed_stop_counts_as_a_shortage(reported):
    client, admin, driver, headers = reported
    assignment = two_shop_trip(client, admin, driver)
    link_ride(client, assignment, driver, headers)
    confirm(client, assignment, headers, "S1", "5", "delivered")
    confirm(client, assignment, headers, "S2", "0", "failed", reason="Shop closed")
    report = client.get("/api/v1/reports/deliveries", headers=admin).json()
    assert [row["customer"] for row in report["shortages"]] == ["City Mart"]
    assert report["product_totals"][0]["delivered_quantity"] == "5"