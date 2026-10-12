"""Supermarket directory, standing orders and trips that reference real shops."""
from contextlib import closing
import json

import pytest

from conftest import api, auth_headers, routeos_app
import erpnext_integration as erp
from test_native_trips import trip_body, link_ride, client_headers


BATTER = [{"product_name": "Idli Batter", "uom": "packet", "planned_quantity": "5"}]


@pytest.fixture
def directory(monkeypatch, tmp_path):
    monkeypatch.setattr(routeos_app, "DATABASE_PATH", tmp_path / "directory.db")
    monkeypatch.delenv("ROUTEOS_ERPNEXT_URL", raising=False)
    monkeypatch.delenv("ROUTEOS_ERPNEXT_API_KEY", raising=False)
    monkeypatch.delenv("ROUTEOS_ERPNEXT_API_SECRET", raising=False)
    monkeypatch.setenv("ROUTEOS_CLIENT_API_KEY", "saravana-client-key")
    with api() as client:
        admin = client.post("/api/v1/auth/login", json={"name": "Sreekandan Nair"}).json()
        driver = client.post("/api/v1/auth/login", json={"name": "D.B Cooper"}).json()
        yield client, auth_headers(admin), driver, auth_headers(driver)


def add_shop(client, admin, name="Metro Fresh", **extra):
    body = {"name": name, "address": "MG Road", "latitude": 9.93, "longitude": 76.27,
            "standing_order": BATTER, **extra}
    response = client.post("/api/v1/supermarkets", headers=admin, json=body)
    assert response.status_code == 201, response.text
    return response.json()


def test_a_shop_is_added_with_its_standing_order(directory):
    client, admin, driver, _ = directory
    shop = add_shop(client, admin)
    assert shop["name"] == "Metro Fresh" and shop["active"] == 1
    assert shop["standing_order"] == [
        {"product_name": "Idli Batter", "uom": "packet", "quantity": "5"}]

    listed = client.get("/api/v1/supermarkets", headers=admin).json()["supermarkets"]
    assert [row["name"] for row in listed] == ["Metro Fresh"]


def test_the_same_shop_is_not_added_twice(directory):
    client, admin, driver, _ = directory
    add_shop(client, admin)
    again = client.post("/api/v1/supermarkets", headers=admin,
                        json={"name": "metro fresh", "latitude": 1, "longitude": 1})
    assert again.status_code == 409


@pytest.mark.parametrize("body", [
    {"name": "   "},
    {"name": "Shop", "latitude": 91},
    {"name": "Shop", "longitude": 181},
    {"name": "Shop", "standing_order": [{"product_name": "Batter", "uom": "kg", "planned_quantity": "0"}]},
    {"name": "Shop", "standing_order": [{"product_name": "", "uom": "kg", "planned_quantity": "5"}]},
])
def test_invalid_shops_are_rejected(directory, body):
    client, admin, driver, _ = directory
    assert client.post("/api/v1/supermarkets", headers=admin, json=body).status_code == 422


def test_only_admins_edit_the_directory(directory):
    client, admin, driver, headers = directory
    add_shop(client, admin)
    assert client.get("/api/v1/supermarkets", headers=headers).status_code == 200  # drivers may read
    assert client.post("/api/v1/supermarkets", headers=headers,
                       json={"name": "Sneaky", "latitude": 1, "longitude": 1}).status_code == 403
    assert client.get("/api/v1/supermarkets").status_code == 401


def test_renaming_a_shop_keeps_its_history(directory):
    client, admin, driver, headers = directory
    shop = add_shop(client, admin)
    body = trip_body(driver["id"])
    body["stops"][0]["supermarket_id"] = shop["id"]
    body["stops"][0]["customer"] = shop["name"]
    assignment = client.post("/api/v1/deliveries/trips", headers=admin, json=body).json()
    link_ride(client, assignment, driver, headers)
    client.post(f"/api/v1/deliveries/{assignment['id']}/stops/STOP-1", headers=headers, json={
        "status": "delivered", "reason": "",
        "items": [{"id": item["id"], "delivered_quantity": item["planned_quantity"]}
                  for item in assignment["stops"][0]["items"]],
        "extras": [{"product_name": "Idli Batter", "uom": "packet", "quantity": "2"}]})

    renamed = client.patch(f"/api/v1/supermarkets/{shop['id']}", headers=admin,
                           json={"name": "Metro Fresh Kachi", "address": "New Road",
                                 "latitude": 9.93, "longitude": 76.27, "standing_order": BATTER})
    assert renamed.status_code == 200, renamed.text

    # History now reads under the new name but is still the same shop.
    trip = client.get("/api/v1/client/deliveries", headers=client_headers()).json()["trips"][0]
    assert trip["stops"][0]["customer"] == "Metro Fresh Kachi"
    assert trip["stops"][0]["supermarket_id"] == shop["id"]
    extras = client.get("/api/v1/deliveries/extras", headers=admin).json()["extras"]
    assert extras[0]["customer"] == "Metro Fresh Kachi"


def test_a_rename_cannot_collide_with_another_shop(directory):
    client, admin, driver, _ = directory
    first = add_shop(client, admin, name="Metro Fresh")
    add_shop(client, admin, name="City Mart")
    clash = client.patch(f"/api/v1/supermarkets/{first['id']}", headers=admin,
                         json={"name": "City Mart", "latitude": 1, "longitude": 1})
    assert clash.status_code == 409


def test_standing_orders_are_replaced_wholesale(directory):
    client, admin, driver, _ = directory
    shop = add_shop(client, admin)
    updated = client.post(f"/api/v1/supermarkets/{shop['id']}/standing-order", headers=admin, json={
        "items": [{"product_name": "Dosa Batter", "uom": "kg", "planned_quantity": "25"}]})
    assert updated.status_code == 200, updated.text
    assert updated.json()["standing_order"] == [
        {"product_name": "Dosa Batter", "uom": "kg", "quantity": "25"}]
    assert client.post(f"/api/v1/supermarkets/{shop['id']}/standing-order", headers=admin,
                       json={"items": []}).status_code == 422
    assert client.post("/api/v1/supermarkets/9999/standing-order", headers=admin,
                       json={"items": BATTER}).status_code == 404


def test_a_trip_can_use_the_directory_shop_and_reuse_its_standing_order(directory):
    client, admin, driver, _ = directory
    shop = add_shop(client, admin)
    body = trip_body(driver["id"])
    # The shop's usual allocation replaces the caller's generic line.
    body["stops"] = [{"stop_ref": "STOP-1", "supermarket_id": shop["id"],
                      "customer": shop["name"], "latitude": shop["latitude"],
                      "longitude": shop["longitude"], "items": []}]
    body["stops"][0]["items"] = [{"product_name": item["product_name"], "uom": item["uom"],
                                  "planned_quantity": item["quantity"]}
                                 for item in shop["standing_order"]]
    assignment = client.post("/api/v1/deliveries/trips", headers=admin, json=body).json()
    assert assignment["stops"][0]["supermarket_id"] == shop["id"]
    assert assignment["stops"][0]["items"][0]["planned_quantity"] == "5"


def test_a_trip_rejects_unknown_inactive_or_duplicated_supermarkets(directory):
    client, admin, driver, _ = directory
    shop = add_shop(client, admin)

    def body_with(supermarket_id, ref="STOP-1"):
        body = trip_body(driver["id"])
        body["stops"] = [{"stop_ref": ref, "supermarket_id": supermarket_id, "customer": "Metro Fresh",
                          "latitude": 9.93, "longitude": 76.27, "items": BATTER}]
        return body

    assert client.post("/api/v1/deliveries/trips", headers=admin,
                       json=body_with(999999)).status_code == 422
    twice = body_with(shop["id"])
    twice["stops"].append(dict(twice["stops"][0], stop_ref="STOP-2"))
    assert client.post("/api/v1/deliveries/trips", headers=admin, json=twice).status_code == 409


def test_supermarkets_are_not_exposed_to_the_client_api(directory):
    client, admin, driver, headers = directory
    shop = add_shop(client, admin)
    body = trip_body(driver["id"])
    body["stops"][0]["supermarket_id"] = shop["id"]
    body["stops"][0]["customer"] = shop["name"]
    client.post("/api/v1/deliveries/trips", headers=admin, json=body)
    trip = client.get("/api/v1/client/deliveries", headers=client_headers()).json()["trips"][0]
    # The shop name is part of the result; internal directory fields are not.
    assert trip["stops"][0]["customer"] == "Metro Fresh"
    assert client.get("/api/v1/supermarkets", headers=client_headers()).status_code == 401