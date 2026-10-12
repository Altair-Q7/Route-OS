"""Moving planned batter between shops so a perishable load is never left over."""
from decimal import Decimal

import pytest

from conftest import api, auth_headers, routeos_app
import erpnext_integration as erp
from test_native_trips import link_ride, client_headers


@pytest.fixture
def transfers(monkeypatch, tmp_path):
    monkeypatch.setattr(routeos_app, "DATABASE_PATH", tmp_path / "transfer.db")
    monkeypatch.delenv("ROUTEOS_ERPNEXT_URL", raising=False)
    monkeypatch.delenv("ROUTEOS_ERPNEXT_API_KEY", raising=False)
    monkeypatch.delenv("ROUTEOS_ERPNEXT_API_SECRET", raising=False)
    monkeypatch.setenv("ROUTEOS_CLIENT_API_KEY", "saravana-client-key")
    with api() as client:
        admin = client.post("/api/v1/auth/login", json={"name": "Sreekandan Nair"}).json()
        driver = client.post("/api/v1/auth/login", json={"name": "D.B Cooper"}).json()
        yield client, auth_headers(admin), driver, auth_headers(driver)


def two_shop_trip(client, admin, driver):
    """Metro Fresh takes 5, City Mart takes 5; both want the same idli batter."""
    body = {
        "trip": "SAP-TRIP-9",
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


def move(client, headers, assignment, **overrides):
    body = {"from_stop_id": "S1", "to_stop_id": "S2", "product_name": "Idli Batter",
            "uom": "packet", "quantity": "2", **overrides}
    return client.post(f"/api/v1/deliveries/{assignment['id']}/transfer", headers=headers, json=body)


def planned(assignment, ref):
    stop = next(item for item in assignment["stops"] if item["id"] == ref)
    return [(item["product_name"], item["uom"], item["planned_quantity"]) for item in stop["items"]]


def test_planned_batter_moves_from_one_shop_to_another(transfers):
    client, admin, driver, headers = transfers
    assignment = two_shop_trip(client, admin, driver)
    result = move(client, admin, assignment).json()
    assert result["stops"][0]["items"][0]["planned_quantity"] == "3"
    assert result["stops"][1]["items"][0]["planned_quantity"] == "7"
    # The trip total is unchanged: nothing was invented or lost.
    assert [(item["product_name"], item["quantity"]) for item in result["surplus"]] == [("Idli Batter", "10")]


def test_only_an_admin_can_move_batter(transfers):
    client, admin, driver, headers = transfers
    assignment = two_shop_trip(client, admin, driver)
    assert move(client, headers, assignment).status_code == 403
    assert move(client, {}, assignment).status_code == 401


def test_batter_can_be_added_to_a_shop_that_does_not_stock_it(transfers):
    client, admin, driver, _ = transfers
    # City Mart normally takes dosa batter only, so idli has to be added to it.
    body = {
        "trip": "SAP-TRIP-10",
        "driver_id": driver["id"],
        "vehicle": "KL-07-AX-1234",
        "stops": [
            {"stop_ref": "S1", "customer": "Metro Fresh", "latitude": 9.93, "longitude": 76.27,
             "items": [{"product_name": "Idli Batter", "uom": "packet", "planned_quantity": "5"}]},
            {"stop_ref": "S2", "customer": "City Mart", "latitude": 9.94, "longitude": 76.28,
             "items": [{"product_name": "Dosa Batter", "uom": "kg", "planned_quantity": "10"}]},
        ],
    }
    created = client.post("/api/v1/deliveries/trips", headers=admin, json=body)
    assert created.status_code == 201, created.text
    assignment = created.json()
    result = client.post(f"/api/v1/deliveries/{assignment['id']}/transfer", headers=admin, json={
        "from_stop_id": "S1", "to_stop_id": "S2", "product_name": "Idli Batter",
        "uom": "packet", "quantity": "2"}).json()
    second = result["stops"][1]["items"]
    dosas = next(item for item in second if item["product_name"] == "Dosa Batter")
    idlis = next(item for item in second if item["product_name"] == "Idli Batter")
    assert dosas["planned_quantity"] == "10"
    assert idlis["planned_quantity"] == "2" and idlis["delivered_quantity"] == "0"


@pytest.mark.parametrize("overrides", [
    {"quantity": "0"},
    {"quantity": "-1"},
    {"quantity": "5"},            # the whole planned amount
    {"quantity": "9"},            # more than is planned
    {"from_stop_id": "S1", "to_stop_id": "S1"},
    {"product_name": "Dosa Batter"},   # not planned on the first shop
    {"uom": "kg"},
])
def test_invalid_transfers_are_rejected(transfers, overrides):
    client, admin, driver, _ = transfers
    assignment = two_shop_trip(client, admin, driver)
    assert move(client, admin, assignment, **overrides).status_code == 422
    assert planned(assignment, "S1")[0][2] == "5"


@pytest.mark.parametrize("overrides", [
    {"from_stop_id": "NOPE"},
    {"to_stop_id": "NOPE"},
])
def test_transfer_to_an_unknown_stop_is_not_found(transfers, overrides):
    client, admin, driver, _ = transfers
    assignment = two_shop_trip(client, admin, driver)
    assert move(client, admin, assignment, **overrides).status_code == 404


def test_batter_cannot_be_moved_once_the_trip_has_started(transfers):
    client, admin, driver, headers = transfers
    assignment = two_shop_trip(client, admin, driver)
    link_ride(client, assignment, driver, headers)
    assert move(client, admin, assignment).status_code == 409


def test_batter_cannot_be_added_to_a_shop_that_already_confirmed(transfers):
    client, admin, driver, headers = transfers
    assignment = two_shop_trip(client, admin, driver)
    link_ride(client, assignment, driver, headers)
    item = next(item for item in assignment["stops"] if item["id"] == "S2")["items"][0]
    confirmed = client.post(f"/api/v1/deliveries/{assignment['id']}/stops/S2", headers=headers, json={
        "status": "delivered",
        "items": [{"id": item["id"], "delivered_quantity": item["planned_quantity"]}]})
    assert confirmed.status_code == 200, confirmed.text
    # The ride has started, so the transfer is refused before this check matters.
    assert move(client, admin, assignment).status_code == 409


def test_surplus_shrinks_as_stops_are_confirmed(transfers):
    client, admin, driver, headers = transfers
    assignment = two_shop_trip(client, admin, driver)
    link_ride(client, assignment, driver, headers)
    assert [(item["product_name"], item["quantity"]) for item in assignment["surplus"]] == [("Idli Batter", "10")]

    item = next(item for item in assignment["stops"] if item["id"] == "S1")["items"][0]
    client.post(f"/api/v1/deliveries/{assignment['id']}/stops/S1", headers=headers, json={
        "status": "delivered",
        "items": [{"id": item["id"], "delivered_quantity": item["planned_quantity"]}]})

    remaining = client.get("/api/v1/deliveries", headers=headers).json()["assignments"][0]
    # Metro Fresh is settled; only City Mart's allocation is still on the van.
    assert [(item["product_name"], item["quantity"]) for item in remaining["surplus"]] == [("Idli Batter", "5")]


def test_a_moved_line_reaches_the_client_as_the_new_plan(transfers):
    client, admin, driver, _ = transfers
    assignment = two_shop_trip(client, admin, driver)
    move(client, admin, assignment)
    trip = client.get("/api/v1/client/deliveries", headers=client_headers()).json()["trips"][0]
    assert [stop["items"][0]["planned_quantity"] for stop in trip["stops"]] == ["3", "7"]


def test_a_transfer_marks_the_trip_changed_for_the_client_cursor(transfers):
    client, admin, driver, _ = transfers
    assignment = two_shop_trip(client, admin, driver)
    cursor = assignment["updated_at"]
    move(client, admin, assignment)
    changed = client.get(f"/api/v1/client/deliveries?since={cursor.replace('+', '%2B')}",
                         headers=client_headers()).json()
    assert changed["count"] == 1


def test_native_transfers_never_reach_erpnext(transfers, monkeypatch):
    client, admin, driver, _ = transfers
    assignment = two_shop_trip(client, admin, driver)
    move(client, admin, assignment)
    monkeypatch.setenv("ROUTEOS_ERPNEXT_URL", "https://erp.example.com")
    monkeypatch.setenv("ROUTEOS_ERPNEXT_API_KEY", "key")
    monkeypatch.setenv("ROUTEOS_ERPNEXT_API_SECRET", "secret")
    calls = []
    monkeypatch.setattr(erp, "erp_request", lambda *a, **k: calls.append(a) or {})
    assert routeos_app.delivery_integration.sync() == {"synced": 0, "failed": 0, "busy": False}
    assert calls == []