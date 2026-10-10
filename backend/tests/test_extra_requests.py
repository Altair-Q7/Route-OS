"""Extra batter requested by a shop: recorded, never handed over, folded into a later trip."""
from contextlib import closing

import pytest

from conftest import api, auth_headers, routeos_app
import erpnext_integration as erp
from test_native_trips import trip_body, link_ride, client_headers


@pytest.fixture
def standalone(monkeypatch, tmp_path):
    monkeypatch.setattr(routeos_app, "DATABASE_PATH", tmp_path / "extras.db")
    monkeypatch.delenv("ROUTEOS_ERPNEXT_URL", raising=False)
    monkeypatch.delenv("ROUTEOS_ERPNEXT_API_KEY", raising=False)
    monkeypatch.delenv("ROUTEOS_ERPNEXT_API_SECRET", raising=False)
    monkeypatch.setenv("ROUTEOS_CLIENT_API_KEY", "saravana-client-key")
    with api() as client:
        admin = client.post("/api/v1/auth/login", json={"name": "Sreekandan Nair"}).json()
        driver = client.post("/api/v1/users", json={"name": "Batter Driver"}).json()
        yield client, auth_headers(admin), driver, auth_headers(driver)


def create_trip(client, admin, driver, trip="SAP-TRIP-1", customer="Metro Fresh"):
    body = trip_body(driver["id"], trip=trip)
    body["stops"][0]["customer"] = customer
    response = client.post("/api/v1/deliveries/trips", headers=admin, json=body)
    assert response.status_code == 201, response.text
    return response.json()


def attach_active_ride(client, assignment, driver, headers):
    """Attach the driver's existing active ride, starting one only if needed."""
    ride = client.get(f"/api/v1/drivers/{driver['id']}/active-ride", headers=headers).json()
    if not isinstance(ride, dict) or "id" not in ride:
        ride = link_ride(client, assignment, driver, headers)
    response = client.post(f"/api/v1/deliveries/{assignment['id']}/ride", headers=headers,
                           json={"ride_id": ride["id"]})
    assert response.status_code == 200, response.text
    return ride


def quantities(assignment):
    """The plan per product, ignoring generated row ids."""
    return [(item["product_name"], item["uom"], item["planned_quantity"])
            for item in assignment["stops"][0]["items"]]


def delivered(assignment):
    return [(item["product_name"], item["delivered_quantity"]) for item in assignment["stops"][0]["items"]]


def end_ride(client, driver, headers):
    ride = client.get(f"/api/v1/drivers/{driver['id']}/active-ride", headers=headers).json()
    if isinstance(ride, dict) and "id" in ride:
        client.post(f"/api/v1/rides/{ride['id']}/end", headers=headers, json={"driver_id": driver["id"]})


def confirm(assignment, client, driver, headers, items, status="delivered", reason="", extras=None):
    body = {"status": status, "reason": reason,
            "items": [{"id": item["id"], "delivered_quantity": quantity}
                      for item, quantity in items]}
    if extras is not None:
        body["extras"] = extras
    response = client.post(f"/api/v1/deliveries/{assignment['id']}/stops/{assignment['stops'][0]['id']}",
                           headers=headers, json=body)
    return response


def full(assignment):
    return [(item, item["planned_quantity"]) for item in assignment["stops"][0]["items"]]


def test_extra_request_is_recorded_without_raising_the_delivered_quantity(standalone):
    client, admin, driver, headers = standalone
    assignment = create_trip(client, admin, driver)
    attach_active_ride(client, assignment, driver, headers)

    response = confirm(assignment, client, driver, headers, full(assignment), extras=[
        {"product_name": "Idli Batter", "uom": "packet", "quantity": "3"}])
    assert response.status_code == 200, response.text
    # The shop asked for more, but the driver handed over exactly the plan.
    assert quantities(response.json()) == quantities(assignment)
    assert delivered(response.json()) == [("Dosa Batter", "25"), ("Idli Batter", "5")]

    pending = client.get("/api/v1/deliveries/extras", headers=admin).json()["extras"]
    assert len(pending) == 1
    assert pending[0] == {'ids': [pending[0]['ids'][0]], 'customer': 'Metro Fresh',
                          'product_name': 'Idli Batter', 'uom': 'packet',
                          'quantity': '3', 'requests': 1}


def test_repeated_identical_confirmation_does_not_duplicate_the_request(standalone):
    client, admin, driver, headers = standalone
    assignment = create_trip(client, admin, driver)
    attach_active_ride(client, assignment, driver, headers)
    extras = [{"product_name": "Idli Batter", "uom": "packet", "quantity": "3"}]
    assert confirm(assignment, client, driver, headers, full(assignment), extras=extras).status_code == 200
    # The same confirmation is retried after a flaky connection.
    assert confirm(assignment, client, driver, headers, full(assignment), extras=extras).status_code == 200
    pending = client.get("/api/v1/deliveries/extras", headers=admin).json()["extras"]
    assert len(pending) == 1 and pending[0]["requests"] == 1


def test_requests_from_several_shops_and_trips_accumulate_per_shop(standalone):
    client, admin, driver, headers = standalone
    first = create_trip(client, admin, driver, trip="SAP-TRIP-1", customer="Metro Fresh")
    attach_active_ride(client, first, driver, headers)
    confirm(first, client, driver, headers, full(first),
            extras=[{"product_name": "Idli Batter", "uom": "packet", "quantity": "3"}])

    # The driver holds one ride at a time, so each later trip follows ending it.
    end_ride(client, driver, headers)
    second = create_trip(client, admin, driver, trip="SAP-TRIP-2", customer="Metro Fresh")
    attach_active_ride(client, second, driver, headers)
    confirm(second, client, driver, headers, full(second),
            extras=[{"product_name": "Idli Batter", "uom": "packet", "quantity": "2"}])

    end_ride(client, driver, headers)
    third = create_trip(client, admin, driver, trip="SAP-TRIP-3", customer="City Mart")
    attach_active_ride(client, third, driver, headers)
    confirm(third, client, driver, headers, full(third),
            extras=[{"product_name": "Dosa Batter", "uom": "kg", "quantity": "4"}])

    pending = {item["customer"]: item for item in
               client.get("/api/v1/deliveries/extras", headers=admin).json()["extras"]}
    # Two trips asked Metro Fresh for idli batter, so they add up per shop.
    assert pending["Metro Fresh"]["product_name"] == "Idli Batter"
    assert pending["Metro Fresh"]["quantity"] == "5"
    assert pending["Metro Fresh"]["requests"] == 2
    # A different shop keeps its own total.
    assert pending["City Mart"]["product_name"] == "Dosa Batter"
    assert pending["City Mart"]["quantity"] == "4"


def test_admin_resolves_a_request_when_it_is_planned_into_a_later_trip(standalone):
    client, admin, driver, headers = standalone
    assignment = create_trip(client, admin, driver)
    attach_active_ride(client, assignment, driver, headers)
    confirm(assignment, client, driver, headers, full(assignment),
            extras=[{"product_name": "Idli Batter", "uom": "packet", "quantity": "3"}])
    pending = client.get("/api/v1/deliveries/extras", headers=admin).json()["extras"]
    ids = pending[0]["ids"]

    assert client.post("/api/v1/deliveries/extras/resolve", headers=headers,
                       json={"ids": ids, "note": "x"}).status_code == 403
    resolved = client.post("/api/v1/deliveries/extras/resolve", headers=admin,
                           json={"ids": ids, "note": "Added to SAP-TRIP-2"})
    assert resolved.status_code == 200 and resolved.json() == {"resolved": 1}
    assert client.get("/api/v1/deliveries/extras", headers=admin).json()["extras"] == []
    # Resolving twice is reported rather than silently succeeding.
    assert client.post("/api/v1/deliveries/extras/resolve", headers=admin,
                       json={"ids": ids, "note": "again"}).status_code == 409


def test_a_failed_stop_still_records_what_the_shop_asked_for(standalone):
    client, admin, driver, headers = standalone
    assignment = create_trip(client, admin, driver)
    attach_active_ride(client, assignment, driver, headers)
    response = confirm(assignment, client, driver, headers, [], status="failed",
                       reason="Shop closed", extras=[
                           {"product_name": "Dosa Batter", "uom": "kg", "quantity": "10"}])
    assert response.status_code == 200, response.text
    pending = client.get("/api/v1/deliveries/extras", headers=admin).json()["extras"]
    assert pending[0]["product_name"] == "Dosa Batter" and pending[0]["quantity"] == "10"


@pytest.mark.parametrize("extra", [
    {"product_name": "Idli Batter", "uom": "packet", "quantity": "0"},
    {"product_name": "Idli Batter", "uom": "packet", "quantity": "-2"},
    {"product_name": "", "uom": "packet", "quantity": "3"},
    {"product_name": "Idli Batter", "uom": "", "quantity": "3"},
    {"product_name": "Idli Batter", "uom": "packet", "quantity": "1.2345"},
])
def test_invalid_extra_requests_are_rejected(standalone, extra):
    client, admin, driver, headers = standalone
    assignment = create_trip(client, admin, driver)
    attach_active_ride(client, assignment, driver, headers)
    assert confirm(assignment, client, driver, headers, full(assignment),
                   extras=[extra]).status_code == 422
    assert client.get("/api/v1/deliveries/extras", headers=admin).json()["extras"] == []


def test_an_extra_request_never_changes_what_the_client_reads(standalone):
    client, admin, driver, headers = standalone
    assignment = create_trip(client, admin, driver)
    attach_active_ride(client, assignment, driver, headers)
    confirm(assignment, client, driver, headers, full(assignment), extras=[
        {"product_name": "Idli Batter", "uom": "packet", "quantity": "3"}])
    trip = client.get("/api/v1/client/deliveries", headers=client_headers()).json()["trips"][0]
    # Extra requests are RouteOS-internal planning input, not a delivered amount.
    assert [(i["product_name"], i["uom"], i["planned_quantity"], i["delivered_quantity"])
            for i in trip["stops"][0]["items"]] == [
                ("Dosa Batter", "kg", "25", "25"), ("Idli Batter", "packet", "5", "5")]
    assert set(trip["stops"][0]) == {"id", "customer", "address_text", "latitude",
                                     "longitude", "status", "reason", "confirmed_at", "items"}


def test_native_trips_with_extras_never_reach_erpnext(standalone, monkeypatch):
    client, admin, driver, headers = standalone
    assignment = create_trip(client, admin, driver)
    attach_active_ride(client, assignment, driver, headers)
    confirm(assignment, client, driver, headers, full(assignment), extras=[
        {"product_name": "Idli Batter", "uom": "packet", "quantity": "3"}])
    monkeypatch.setenv("ROUTEOS_ERPNEXT_URL", "https://erp.example.com")
    monkeypatch.setenv("ROUTEOS_ERPNEXT_API_KEY", "key")
    monkeypatch.setenv("ROUTEOS_ERPNEXT_API_SECRET", "secret")
    calls = []
    monkeypatch.setattr(erp, "erp_request", lambda *a, **k: calls.append(a) or {})
    assert routeos_app.delivery_integration.sync() == {"synced": 0, "failed": 0, "busy": False}
    assert calls == []