"""Native (ERPNext-free) trip creation, read-only client access and ERP isolation."""
from contextlib import closing
import json
from urllib.parse import quote

import pytest

from conftest import api, auth_headers, routeos_app
import erpnext_integration as erp
from test_rides import _driver, _route, _start, _locate


CLIENT_KEY = "saravana-client-key"
TRIP_VEHICLE = "KL-07-AX-1234"


def start_ride(client, driver, headers, route_id, vehicle=TRIP_VEHICLE):
    """Start a ride, mirroring test_rides._start but with the trip's vehicle number."""
    response = client.post("/api/v1/rides", headers=headers, json={
        "driver_id": driver["id"], "route_id": route_id, "vehicle_type": "auto",
        "vehicle_number": vehicle,
    })
    assert response.status_code == 201, response.text
    return response.json()


def link_ride(client, assignment, driver, headers):
    """Create a route, start a matching ride and attach it to the trip."""
    route = _route(client, driver, headers)
    ride = start_ride(client, driver, headers, route["id"])
    result = client.post(f"/api/v1/deliveries/{assignment['id']}/ride", headers=headers,
                         json={"ride_id": ride["id"]})
    assert result.status_code == 200, result.text
    return ride


def trip_body(driver_id: int, **overrides):
    body = {
        "trip": "SAP-TRIP-1042",
        "driver_id": driver_id,
        "vehicle": "KL-07-AX-1234",
        "stops": [{
            "stop_ref": "STOP-1",
            "customer": "Metro Fresh",
            "address": "MG Road",
            "latitude": 9.93,
            "longitude": 76.27,
            "items": [
                {"product_name": "Dosa Batter", "uom": "kg", "planned_quantity": 25},
                {"product_name": "Idli Batter", "uom": "packet", "planned_quantity": 5},
            ],
        }],
    }
    body.update(overrides)
    return body


@pytest.fixture
def native(monkeypatch, tmp_path):
    """No ERPNext configuration at all: the standalone delivery flow must work."""
    monkeypatch.setattr(routeos_app, "DATABASE_PATH", tmp_path / "native.db")
    monkeypatch.delenv("ROUTEOS_ERPNEXT_URL", raising=False)
    monkeypatch.delenv("ROUTEOS_ERPNEXT_API_KEY", raising=False)
    monkeypatch.delenv("ROUTEOS_ERPNEXT_API_SECRET", raising=False)
    monkeypatch.setenv("ROUTEOS_CLIENT_API_KEY", CLIENT_KEY)
    with api() as client:
        admin = client.post("/api/v1/auth/login", json={"name": "Sreekandan Nair"}).json()
        driver, headers = _driver(client, "Batter Driver")
        yield client, auth_headers(admin), driver, headers


def client_headers():
    return {"X-RouteOS-Client-Key": CLIENT_KEY}


def test_admin_creates_a_native_trip_without_erpnext(native):
    client, admin, driver, _ = native
    response = client.post("/api/v1/deliveries/trips", headers=admin, json=trip_body(driver["id"]))
    assert response.status_code == 201, response.text
    assignment = response.json()
    assert assignment["trip"] == "SAP-TRIP-1042"
    assert assignment["status"] == "Assigned"
    assert assignment["vehicle"] == "KL-07-AX-1234"
    stop = assignment["stops"][0]
    assert stop["customer"] == "Metro Fresh" and stop["status"] == "pending"
    assert [(item["product_name"], item["uom"], item["planned_quantity"]) for item in stop["items"]] == [
        ("Dosa Batter", "kg", "25"), ("Idli Batter", "packet", "5")]
    assert all(item["delivered_quantity"] == "0" for item in stop["items"])


def test_only_admin_can_create_a_native_trip(native):
    client, _, driver, headers = native
    assert client.post("/api/v1/deliveries/trips", headers=headers, json=trip_body(driver["id"])).status_code == 403
    assert client.post("/api/v1/deliveries/trips", json=trip_body(driver["id"])).status_code == 401


@pytest.mark.parametrize("overrides", [
    {"driver_id": 999999},
    {"trip": "   "},
    {"stops": []},
])
def test_invalid_trip_reference_driver_and_stops_are_rejected(native, overrides):
    client, admin, driver, _ = native
    body = trip_body(driver["id"])
    body.update(overrides)
    assert client.post("/api/v1/deliveries/trips", headers=admin, json=body).status_code == 422


@pytest.mark.parametrize("stop", [
    {"stop_ref": "", "customer": "Metro Fresh", "latitude": 9.93, "longitude": 76.27,
     "items": [{"product_name": "Dosa Batter", "uom": "kg", "planned_quantity": 25}]},
    {"stop_ref": "STOP-1", "customer": "  ", "latitude": 9.93, "longitude": 76.27,
     "items": [{"product_name": "Dosa Batter", "uom": "kg", "planned_quantity": 25}]},
    {"stop_ref": "STOP-1", "customer": "Metro Fresh", "latitude": 91, "longitude": 76.27,
     "items": [{"product_name": "Dosa Batter", "uom": "kg", "planned_quantity": 25}]},
    {"stop_ref": "STOP-1", "customer": "Metro Fresh", "latitude": 9.93, "longitude": 76.27, "items": []},
    {"stop_ref": "STOP-1", "customer": "Metro Fresh", "latitude": 9.93, "longitude": 76.27,
     "items": [{"product_name": "Dosa Batter", "uom": "kg", "planned_quantity": 0}]},
    {"stop_ref": "STOP-1", "customer": "Metro Fresh", "latitude": 9.93, "longitude": 76.27,
     "items": [{"product_name": "Dosa Batter", "uom": "kg", "planned_quantity": 1.2345}]},
])
def test_invalid_stop_and_product_rows_are_rejected(native, stop):
    client, admin, driver, _ = native
    body = trip_body(driver["id"])
    body["stops"] = [stop]
    assert client.post("/api/v1/deliveries/trips", headers=admin, json=body).status_code == 422


def test_duplicate_stop_reference_is_rejected(native):
    client, admin, driver, _ = native
    body = trip_body(driver["id"])
    body["stops"] = body["stops"] * 2
    assert client.post("/api/v1/deliveries/trips", headers=admin, json=body).status_code == 422


def test_recreating_the_same_trip_does_not_duplicate_or_reset_confirmations(native):
    client, admin, driver, headers = native
    assignment = client.post("/api/v1/deliveries/trips", headers=admin, json=trip_body(driver["id"])).json()
    link_ride(client, assignment, driver, headers)
    confirmed = client.post(f"/api/v1/deliveries/{assignment['id']}/stops/STOP-1", headers=headers, json={
        "status": "delivered",
        "items": [{"id": item["id"], "delivered_quantity": item["planned_quantity"]}
                  for item in assignment["stops"][0]["items"]],
    })
    assert confirmed.status_code == 200, confirmed.text

    retry = client.post("/api/v1/deliveries/trips", headers=admin, json=trip_body(driver["id"]))
    assert retry.status_code == 201
    assert retry.json()["id"] == assignment["id"]
    assert retry.json()["stops"][0]["status"] == "delivered"
    assert len(client.get("/api/v1/deliveries", headers=admin).json()["assignments"]) == 1


def test_native_trip_cannot_be_reassigned_to_another_driver(native):
    client, admin, driver, _ = native
    client.post("/api/v1/deliveries/trips", headers=admin, json=trip_body(driver["id"]))
    other, _ = _driver(client, "Second Batter Driver")
    response = client.post("/api/v1/deliveries/trips", headers=admin, json=trip_body(other["id"]))
    assert response.status_code == 409


def test_native_trip_cannot_target_an_admin_account(native):
    client, admin, _, _ = native
    admin_id = client.post("/api/v1/auth/login", json={"name": "Sreekandan Nair"}).json()["id"]
    assert client.post("/api/v1/deliveries/trips", headers=admin, json=trip_body(admin_id)).status_code == 422


def test_native_trip_quantity_confirmation_and_kg_packet_totals(native):
    client, admin, driver, headers = native
    assignment = client.post("/api/v1/deliveries/trips", headers=admin, json=trip_body(driver["id"])).json()
    link_ride(client, assignment, driver, headers)
    items = assignment["stops"][0]["items"]
    dosa = next(item for item in items if item["uom"] == "kg")

    # Over-delivery stays rejected for natively built trips too.
    assert client.post(f"/api/v1/deliveries/{assignment['id']}/stops/STOP-1", headers=headers, json={
        "status": "delivered",
        "items": [{"id": dosa["id"], "delivered_quantity": "26"},
                  {"id": next(item for item in items if item["uom"] == "packet")["id"], "delivered_quantity": "5"}],
    }).status_code == 422

    result = client.post(f"/api/v1/deliveries/{assignment['id']}/stops/STOP-1", headers=headers, json={
        "status": "partial", "reason": "Shop had no storage",
        "items": [{"id": dosa["id"], "delivered_quantity": "22"},
                  {"id": next(item for item in items if item["uom"] == "packet")["id"], "delivered_quantity": "5"}],
    })
    assert result.status_code == 200, result.text
    payload = result.json()
    assert payload["status"] == "Closed with shortages"
    totals = {(item["uom"]): item for item in payload["product_totals"]}
    assert totals["kg"]["planned_quantity"] == "25" and totals["kg"]["delivered_quantity"] == "22"
    assert totals["packet"]["planned_quantity"] == "5" and totals["packet"]["delivered_quantity"] == "5"


def test_native_trip_never_syncs_to_erpnext(native, monkeypatch):
    client, admin, driver, _ = native
    client.post("/api/v1/deliveries/trips", headers=admin, json=trip_body(driver["id"]))
    monkeypatch.setenv("ROUTEOS_ERPNEXT_URL", "https://erp.example.com")
    monkeypatch.setenv("ROUTEOS_ERPNEXT_API_KEY", "key")
    monkeypatch.setenv("ROUTEOS_ERPNEXT_API_SECRET", "secret")
    calls = []
    monkeypatch.setattr(erp, "erp_request", lambda *a, **k: calls.append(a) or {})

    assert routeos_app.delivery_integration.sync() == {"synced": 0, "failed": 0, "busy": False}
    assert calls == []
    with closing(routeos_app.connection()) as db:
        row = db.execute("SELECT source, site, erp_driver FROM delivery_assignments").fetchone()
    assert row["source"] == "native" and row["site"] is None and row["erp_driver"] is None


def test_erp_sync_error_leaves_the_app_working_without_erpnext(native, monkeypatch):
    client, admin, driver, _ = native
    client.post("/api/v1/deliveries/trips", headers=admin, json=trip_body(driver["id"]))
    monkeypatch.setenv("ROUTEOS_ERPNEXT_URL", "https://erp.example.com")
    monkeypatch.setenv("ROUTEOS_ERPNEXT_API_KEY", "key")
    monkeypatch.setenv("ROUTEOS_ERPNEXT_API_SECRET", "secret")
    monkeypatch.setattr(erp, "erp_request", lambda *a, **k: (_ for _ in ()).throw(OSError("down")))
    assert routeos_app.delivery_integration.sync() == {"synced": 0, "failed": 0, "busy": False}
    assert client.get("/health").status_code == 200


def test_client_reads_trips_with_its_key(native):
    client, admin, driver, headers = native
    assignment = client.post("/api/v1/deliveries/trips", headers=admin, json=trip_body(driver["id"])).json()
    result = client.get("/api/v1/client/deliveries", headers=client_headers())
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["count"] == 1
    trip = body["trips"][0]
    assert trip["trip"] == "SAP-TRIP-1042"
    assert trip["driver_name"] == "Batter Driver"
    assert trip["stops"][0]["customer"] == "Metro Fresh"
    assert [(item["uom"], item["planned_quantity"]) for item in trip["stops"][0]["items"]] == [("kg", "25"), ("packet", "5")]

    detail = client.get(f"/api/v1/client/deliveries/{assignment['id']}", headers=client_headers())
    assert detail.status_code == 200
    assert detail.json()["id"] == assignment["id"]
    assert client.get("/api/v1/client/deliveries/999999", headers=client_headers()).status_code == 404


def test_client_response_hides_erp_sync_internals(native):
    client, admin, driver, _ = native
    client.post("/api/v1/deliveries/trips", headers=admin, json=trip_body(driver["id"]))
    trip = client.get("/api/v1/client/deliveries", headers=client_headers()).json()["trips"][0]
    # `site` can hold the customer's own ERP URL, and the rest is internal retry state.
    assert set(trip) == {"id", "trip", "status", "driver_id", "driver_name", "vehicle",
                         "created_at", "updated_at", "ride", "location", "stops",
                         "product_totals"}
    assert set(trip["stops"][0]) == {"id", "supermarket_id", "customer", "address_text", "latitude",
                                     "longitude", "status", "reason", "confirmed_at", "items"}
    assert set(trip["stops"][0]["items"][0]) == {"product_name", "uom",
                                                 "planned_quantity", "delivered_quantity"}


def test_client_key_is_required_and_read_only(native):
    client, admin, driver, headers = native
    assignment = client.post("/api/v1/deliveries/trips", headers=admin, json=trip_body(driver["id"])).json()
    assert client.get("/api/v1/client/deliveries").status_code == 401
    assert client.get("/api/v1/client/deliveries", headers={"X-RouteOS-Client-Key": "wrong"}).status_code == 401
    # A client key must never allow creating trips or confirming deliveries.
    assert client.post("/api/v1/deliveries/trips", headers=client_headers(), json=trip_body(driver["id"])).status_code == 401
    assert client.post(f"/api/v1/deliveries/{assignment['id']}/stops/STOP-1", headers=client_headers(),
                       json={"status": "failed", "reason": "no"}).status_code == 401


def test_client_access_requires_configuration(monkeypatch, tmp_path):
    monkeypatch.setattr(routeos_app, "DATABASE_PATH", tmp_path / "nokey.db")
    monkeypatch.delenv("ROUTEOS_CLIENT_API_KEY", raising=False)
    with api() as client:
        assert client.get("/api/v1/client/deliveries", headers=client_headers()).status_code == 503


def test_driver_list_is_admin_only_and_ordered(native):
    client, _, driver, headers = native
    assert client.get("/api/v1/drivers", headers=headers).status_code == 403
    assert client.get("/api/v1/drivers").status_code == 401
    _driver(client, "Anil Batter Driver")
    listed = client.get("/api/v1/drivers", headers=admin_headers(native)).json()["drivers"]
    assert [row["name"] for row in listed] == sorted(row["name"] for row in listed)
    assert driver["id"] in [row["id"] for row in listed]
    assert "Sreekandan Nair" not in [row["name"] for row in listed]  # admins are not assignable


def admin_headers(native):
    return native[1]


def test_client_polling_cursor_and_validation(native):
    client, admin, driver, headers = native
    assignment = client.post("/api/v1/deliveries/trips", headers=admin, json=trip_body(driver["id"])).json()
    first = client.get("/api/v1/client/deliveries", headers=client_headers()).json()
    assert first["count"] == 1

    # A cursor captured after creation must exclude the unchanged trip, otherwise
    # every poll would re-download it forever.
    cursor = first["trips"][0]["updated_at"]
    assert client.get(f"/api/v1/client/deliveries?since={quote(cursor)}",
                      headers=client_headers()).json()["count"] == 0

    # Confirming a stop counts as a change, so the client learns about the result.
    link_ride(client, assignment, driver, headers)
    confirmed = client.post(f"/api/v1/deliveries/{assignment['id']}/stops/STOP-1", headers=headers, json={
        "status": "delivered",
        "items": [{"id": item["id"], "delivered_quantity": item["planned_quantity"]}
                  for item in assignment["stops"][0]["items"]],
    })
    assert confirmed.status_code == 200, confirmed.text
    updated = client.get(f"/api/v1/client/deliveries?since={quote(cursor)}", headers=client_headers()).json()
    assert updated["count"] == 1
    assert updated["trips"][0]["stops"][0]["status"] == "delivered"

    assert client.get("/api/v1/client/deliveries?since=yesterday", headers=client_headers()).status_code == 422

    # A raw '+' in the query string decodes to a space, which the client must
    # avoid by percent-encoding the timestamp.
    unencoded = client.get(f"/api/v1/client/deliveries?since={cursor}", headers=client_headers())
    assert unencoded.status_code in (200, 422)
    encoded = client.get(f"/api/v1/client/deliveries?since={quote(cursor)}", headers=client_headers())
    assert encoded.status_code == 200


def test_existing_rows_get_a_change_timestamp_on_migration(native):
    client, admin, driver, _ = native
    client.post("/api/v1/deliveries/trips", headers=admin, json=trip_body(driver["id"]))
    with closing(routeos_app.connection()) as db:
        db.execute("UPDATE delivery_assignments SET updated_at=NULL")
        db.commit()
    with closing(routeos_app.connection()) as db:
        erp.initialize(db)
        db.commit()
        row = db.execute("SELECT updated_at,created_at FROM delivery_assignments").fetchone()
    assert row["updated_at"] == row["created_at"]


def test_a_legacy_database_migrates_without_losing_deliveries(native, tmp_path):
    """Trips built before the supermarket table existed must survive the upgrade."""
    client, admin, driver, _ = native
    assignment = client.post("/api/v1/deliveries/trips", headers=admin, json=trip_body(driver["id"])).json()

    # Recreate the pre-upgrade shape: no source column, site held the sentinel.
    with closing(routeos_app.connection()) as db:
        db.executescript("""
            DROP TABLE delivery_assignments;
            CREATE TABLE delivery_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT, site TEXT NOT NULL, trip TEXT NOT NULL,
                driver_id INTEGER NOT NULL REFERENCES users(id), erp_driver TEXT NOT NULL,
                ride_id INTEGER UNIQUE REFERENCES rides(id), vehicle TEXT, departure_time TEXT,
                stops TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
                synced_revision INTEGER NOT NULL DEFAULT 0, last_sync TEXT, last_error TEXT,
                attempts INTEGER NOT NULL DEFAULT 0, next_attempt TEXT, created_at TEXT NOT NULL);
        """)
        stops = json.dumps([{"id": "STOP-1", "customer": "Metro Fresh", "status": "pending",
                             "reason": "", "items": [], "latitude": 9.93, "longitude": 76.27}])
        db.execute("""INSERT INTO delivery_assignments
            (site,trip,driver_id,erp_driver,vehicle,stops,created_at) VALUES (?,?,?,?,?,?,?)""",
            ("native", assignment["trip"], driver["id"], "", "KL-07-AX-1234", stops, "2026-09-01T00:00:00+00:00"))
        db.commit()
        erp.initialize(db)
        db.commit()
        row = db.execute("SELECT * FROM delivery_assignments").fetchone()

    assert row["source"] == "native"
    assert row["site"] is None and row["erp_driver"] is None
    assert row["trip"] == assignment["trip"]
    # The shop named on an old stop becomes a directory entry and is linked back.
    assert json.loads(row["stops"])[0]["supermarket_id"] is not None
    shops = client.get("/api/v1/supermarkets", headers=admin).json()["supermarkets"]
    assert [shop["name"] for shop in shops] == ["Metro Fresh"]


def test_driver_sees_only_own_native_trip_and_admin_sees_all(native):
    client, admin, driver, headers = native
    client.post("/api/v1/deliveries/trips", headers=admin, json=trip_body(driver["id"]))
    other, other_headers = _driver(client, "Unrelated Driver")
    mine = client.get("/api/v1/deliveries", headers=headers).json()["assignments"]
    assert [row["trip"] for row in mine] == ["SAP-TRIP-1042"]
    assert client.get("/api/v1/deliveries", headers=other_headers).json()["assignments"] == []
    assert len(client.get("/api/v1/deliveries", headers=admin).json()["assignments"]) == 1
    # The client system sees every trip, which is the point of a shared reporting feed.
    assert client.get("/api/v1/client/deliveries", headers=client_headers()).json()["count"] == 1


def test_ride_vehicle_number_must_match_a_native_trip(native):
    client, admin, driver, headers = native
    assignment = client.post("/api/v1/deliveries/trips", headers=admin, json=trip_body(driver["id"])).json()
    route = _route(client, driver, headers)
    wrong = start_ride(client, driver, headers, route["id"], vehicle="WRONG")
    assert client.post(f"/api/v1/deliveries/{assignment['id']}/ride", headers=headers,
                       json={"ride_id": wrong["id"]}).status_code == 409
    # A driver may only hold one active ride, so reuse it after ending the rejected one.
    assert client.post(f"/api/v1/rides/{wrong['id']}/end", headers=headers,
                       json={"driver_id": driver["id"]}).status_code == 200
    # The comparison is case-insensitive, so drivers need not retype the plate exactly.
    ride = start_ride(client, driver, headers, _route(client, driver, headers, name="Second route")["id"],
                      vehicle=TRIP_VEHICLE.lower())
    assert client.post(f"/api/v1/deliveries/{assignment['id']}/ride", headers=headers,
                       json={"ride_id": ride["id"]}).status_code == 200


def test_native_trip_records_gps_evidence_for_the_client(native):
    client, admin, driver, headers = native
    assignment = client.post("/api/v1/deliveries/trips", headers=admin, json=trip_body(driver["id"])).json()
    ride = link_ride(client, assignment, driver, headers)
    _locate(client, driver, headers, ride["id"], 9.93, 76.27)
    trip = client.get(f"/api/v1/client/deliveries/{assignment['id']}", headers=client_headers()).json()
    assert trip["location"]["latitude"] == 9.93 and trip["location"]["longitude"] == 76.27
    assert trip["ride"]["status"] == "active"