"""ERP delivery isolation, ownership, confirmation and durable retry coverage."""
from contextlib import closing
import json
import pytest
from fastapi import HTTPException

from conftest import api, auth_headers, routeos_app
import erpnext_integration as erp
from test_rides import _driver, _route, _start, _locate


@pytest.fixture
def integration(monkeypatch, tmp_path):
    monkeypatch.setattr(routeos_app, "DATABASE_PATH", tmp_path / "deliveries.db")
    monkeypatch.setenv("ROUTEOS_ERPNEXT_URL", "http://127.0.0.1:8080")
    monkeypatch.setenv("ROUTEOS_ERPNEXT_API_KEY", "test-key")
    monkeypatch.setenv("ROUTEOS_ERPNEXT_API_SECRET", "test-secret")
    requests = []
    documents = {}
    trip = {"name": "MAT-DT-TEST", "driver": "ERP-DRIVER", "docstatus": 1,
            "status": "Scheduled", "vehicle": "KL-01-AB-1234", "departure_time": "2026-10-09 19:00:00",
            "delivery_stops": [{"name": "STOP-1", "customer": "Customer A", "address": "Address A",
                                "customer_address": "<b>Street</b>", "delivery_note": "DN-TEST", "lat": 12.9, "lng": 77.6}]}

    def request(method, path, body=None, query=None):
        requests.append((method, path, body))
        if path.startswith("/api/resource/Delivery Trip/"):
            return trip
        if path == "/api/resource/Delivery Trip":
            return [trip]
        if path.startswith('/api/resource/Delivery Note/'):
            return {'docstatus':1, 'customer':'Customer A', 'items':[
                {'name':'MILK-ROW', 'item_code':'MILK', 'item_name':'Milk', 'qty':10, 'uom':'L'},
                {'name':'BATTER-ROW', 'item_code':'BATTER', 'item_name':'Batter', 'qty':2, 'uom':'kg'},
            ]}
        if method == "GET":
            name = json.loads(query["filters"])[0][2]
            return [{"name": name}] if name in documents else []
        documents[body["routeos_reference"]] = body
        return body

    monkeypatch.setattr(erp, "erp_request", request)
    with api() as client:
        admin = client.post("/api/v1/auth/login", json={"name": "Sreekandan Nair"}).json()
        driver, headers = _driver(client, "Delivery Driver")
        yield client, auth_headers(admin), driver, headers, trip, requests, documents


def assign(fixture):
    client, admin, driver, _, trip, *_ = fixture
    result = client.post("/api/v1/erpnext/import", headers=admin,
                         json={"trip": trip["name"], "driver_id": driver["id"]})
    assert result.status_code == 201, result.text
    return result.json()


def link(fixture, assignment):
    client, _, driver, headers, *_ = fixture
    route = _route(client, driver, headers)
    ride = _start(client, driver, headers, route["id"]).json()
    result = client.post(f"/api/v1/deliveries/{assignment['id']}/ride", headers=headers, json={"ride_id": ride["id"]})
    assert result.status_code == 200, result.text
    return ride


def full_delivery():
    return {'status':'delivered', 'items':[
        {'id':'MILK-ROW', 'delivered_quantity':'10'},
        {'id':'BATTER-ROW', 'delivered_quantity':'2'},
    ]}


def test_driver_cannot_import_sync_or_view_another_drivers_delivery(integration):
    client, _, driver, headers, *_ = integration
    assignment = assign(integration)
    assert client.get("/api/v1/erpnext/catalog", headers=headers).status_code == 403
    assert client.post("/api/v1/erpnext/sync", headers=headers).status_code == 403
    assert client.post("/api/v1/erpnext/import", headers=headers,
                       json={"trip": "test", "driver_id": driver["id"]}).status_code == 403
    _, other_headers = _driver(client, "Other Delivery Driver")
    assert client.get("/api/v1/deliveries", headers=other_headers).json()["assignments"] == []
    assert client.post(f"/api/v1/deliveries/{assignment['id']}/stops/STOP-1", headers=other_headers,
                       json={"status": "delivered"}).status_code == 403
    assert client.get("/api/v1/deliveries").status_code == 401


def test_gps_and_ride_end_do_not_confirm_delivery(integration):
    client, _, driver, headers, *_ = integration
    assignment = assign(integration)
    ride = link(integration, assignment)
    _locate(client, driver, headers, ride["id"], 12.9, 77.6)
    client.post(f"/api/v1/rides/{ride['id']}/end", headers=headers, json={"driver_id": driver["id"]})
    result = client.get("/api/v1/deliveries", headers=headers).json()["assignments"][0]
    assert result["stops"][0]["status"] == "pending"
    assert result["ride"]["status"] == "ended"
    assert result["location"]["latitude"] == 12.9


def test_confirmation_is_idempotent_and_reimport_preserves_evidence(integration):
    client, _, _, headers, _, _, documents = integration
    assignment = assign(integration)
    link(integration, assignment)
    path = f"/api/v1/deliveries/{assignment['id']}/stops/STOP-1"
    first = client.post(path, headers=headers, json=full_delivery()).json()
    retry = client.post(path, headers=headers, json=full_delivery()).json()
    assert first["stops"] == retry["stops"]
    assert len(retry["events"]) == 1
    assert client.post(path, headers=headers, json={"status": "arrived"}).status_code == 409
    assert assign(integration)["stops"][0]["status"] == "delivered"
    assert routeos_app.delivery_integration.sync()["synced"] == 1
    assert len(documents) == 1
    assert routeos_app.delivery_integration.sync()["synced"] == 1  # live GPS refresh uses same ERP document
    assert len(documents) == 1
    assert all("tracking" in path.lower() for method, path, _ in integration[5] if method in ("POST", "PUT"))


def test_failures_require_reason_and_linked_ride(integration):
    client, _, _, headers, *_ = integration
    assignment = assign(integration)
    path = f"/api/v1/deliveries/{assignment['id']}/stops/STOP-1"
    assert client.post(path, headers=headers, json={"status": "failed"}).status_code == 422
    assert client.post(path, headers=headers, json={"status": "failed", "reason": "Absent"}).status_code == 409
    link(integration, assignment)
    result = client.post(path, headers=headers, json={"status": "failed", "reason": "Absent"})
    assert result.json()["status"] == "Closed with failures"
    assert result.json()["events"][0]["reason"] == "Absent"


def test_erp_outage_retains_updates_and_retry_clears_error(integration, monkeypatch):
    client, admin, _, headers, *_ = integration
    assignment = assign(integration)
    original = erp.erp_request
    def offline(*args, **kwargs):
        raise HTTPException(502, "ERPNext unavailable")
    monkeypatch.setattr(erp, "erp_request", offline)
    assert routeos_app.delivery_integration.sync()["failed"] == 1
    row = client.get("/api/v1/deliveries", headers=headers).json()["assignments"][0]
    assert row["sync_pending"] and row["last_error"]
    assert routeos_app.delivery_integration.sync()["failed"] == 0  # backoff
    assert client.post("/api/v1/erpnext/sync", headers=admin).json() == {"queued": True}
    monkeypatch.setattr(erp, "erp_request", original)
    assert routeos_app.delivery_integration.sync()["synced"] == 1
    row = client.get("/api/v1/deliveries", headers=headers).json()["assignments"][0]
    assert not row["sync_pending"] and row["last_error"] is None
    with closing(routeos_app.connection()) as db:
        assert db.execute("SELECT COUNT(*) FROM delivery_assignments WHERE id=?", (assignment["id"],)).fetchone()[0] == 1


def test_ride_end_is_synced_even_after_last_active_snapshot(integration):
    client, _, driver, headers, *_ = integration
    assignment = assign(integration)
    ride = link(integration, assignment)
    assert routeos_app.delivery_integration.sync()["synced"] == 1
    client.post(f"/api/v1/rides/{ride['id']}/end", headers=headers, json={"driver_id": driver["id"]})
    assert routeos_app.delivery_integration.sync()["synced"] == 1
    assert routeos_app.delivery_integration.sync()["synced"] == 0
    snapshot = json.loads(next(iter(integration[6].values()))["tracking_data"])
    assert snapshot["ride"]["status"] == "ended"
    assert snapshot["status"] != "Delivered"


def test_unsubmitted_trip_is_not_imported(integration):
    client, admin, driver, _, trip, *_ = integration
    trip["docstatus"] = 0
    assert client.post("/api/v1/erpnext/import", headers=admin,
                       json={"trip": trip["name"], "driver_id": driver["id"]}).status_code == 409


def test_unconfigured_integration_does_not_break_existing_app(integration, monkeypatch):
    client, admin, _, _, *_ = integration
    monkeypatch.delenv("ROUTEOS_ERPNEXT_API_SECRET")
    assert client.get("/health").status_code == 200
    assert client.get("/api/v1/deliveries", headers=admin).status_code == 200
    assert client.post("/api/v1/erpnext/sync", headers=admin).status_code == 503


def test_remote_plain_http_and_credential_urls_are_rejected(monkeypatch):
    monkeypatch.setenv("ROUTEOS_ERPNEXT_API_KEY", "key")
    monkeypatch.setenv("ROUTEOS_ERPNEXT_API_SECRET", "secret")
    for url in ("http://example.com", "https://user:secret@example.com", "https://example.com?secret=x"):
        monkeypatch.setenv("ROUTEOS_ERPNEXT_URL", url)
        with pytest.raises(HTTPException):
            erp.configuration()


def test_http_client_encodes_doctype_names_and_does_not_follow_redirects(monkeypatch):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import threading
    paths = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            paths.append(self.path)
            if self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", "/leaked-secret")
                self.end_headers()
            else:
                assert self.headers["Authorization"] == "token key:secret"
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"data": []}')

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    monkeypatch.setenv("ROUTEOS_ERPNEXT_URL", f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setenv("ROUTEOS_ERPNEXT_API_KEY", "key")
    monkeypatch.setenv("ROUTEOS_ERPNEXT_API_SECRET", "secret")
    try:
        assert erp.erp_request("GET", "/api/resource/Delivery Trip") == []
        assert paths == ["/api/resource/Delivery%20Trip"]
        with pytest.raises(HTTPException):
            erp.erp_request("GET", "/redirect")
        assert "/leaked-secret" not in paths
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_vehicle_and_driver_mapping_are_checked(integration):
    client, admin, driver, headers, trip, *_ = integration
    assignment = assign(integration)
    route = _route(client, driver, headers)
    ride = client.post("/api/v1/rides", headers=headers, json={
        "driver_id": driver["id"], "route_id": route["id"], "vehicle_type": "auto", "vehicle_number": "WRONG",
    }).json()
    assert client.post(f"/api/v1/deliveries/{assignment['id']}/ride", headers=headers,
                       json={"ride_id": ride["id"]}).status_code == 409
    other, _ = _driver(client, "Another mapped driver")
    assert client.post("/api/v1/erpnext/import", headers=admin,
                       json={"trip": trip["name"], "driver_id": other["id"]}).status_code == 409


def test_ride_end_during_erp_request_is_not_lost(integration, monkeypatch):
    client, _, driver, headers, *_ = integration
    assignment = assign(integration)
    ride = link(integration, assignment)
    original = erp.erp_request
    ended = False
    def request(*args, **kwargs):
        nonlocal ended
        if not ended:
            ended = True
            client.post(f"/api/v1/rides/{ride['id']}/end", headers=headers, json={"driver_id": driver["id"]})
        return original(*args, **kwargs)
    monkeypatch.setattr(erp, "erp_request", request)
    assert routeos_app.delivery_integration.sync()["synced"] == 1
    assert routeos_app.delivery_integration.sync()["synced"] == 1
    snapshot = json.loads(next(iter(integration[6].values()))["tracking_data"])
    assert snapshot["ride"]["status"] == "ended"


def test_product_manifest_is_imported_with_names_units_and_quantities(integration):
    assignment = assign(integration)
    milk, batter = assignment['stops'][0]['items']
    assert milk['product_name'] == 'Milk' and milk['uom'] == 'L'
    assert milk['planned_quantity'] == '10' and milk['delivered_quantity'] == '0'
    assert batter['product_name'] == 'Batter' and batter['uom'] == 'kg'
    assert any(path.startswith('/api/resource/Delivery Note/') for _, path, _ in integration[5])


@pytest.mark.parametrize('items', [
    [], [{'id':'MILK-ROW','delivered_quantity':10}],
    [{'id':'MILK-ROW','delivered_quantity':11}, {'id':'BATTER-ROW','delivered_quantity':2}],
    [{'id':'MILK-ROW','delivered_quantity':-1}, {'id':'BATTER-ROW','delivered_quantity':2}],
    [{'id':'MILK-ROW','delivered_quantity':10}, {'id':'MILK-ROW','delivered_quantity':10}],
    [{'id':'UNKNOWN','delivered_quantity':10}, {'id':'BATTER-ROW','delivered_quantity':2}],
    [{'id':'MILK-ROW','delivered_quantity':'NaN'}, {'id':'BATTER-ROW','delivered_quantity':2}],
    [{'id':'MILK-ROW','delivered_quantity':'1.2345'}, {'id':'BATTER-ROW','delivered_quantity':2}],
])
def test_invalid_delivery_quantities_are_rejected(integration, items):
    client, _, _, headers, *_ = integration
    assignment = assign(integration)
    link(integration, assignment)
    response = client.post(f"/api/v1/deliveries/{assignment['id']}/stops/STOP-1", headers=headers,
                           json={'status':'delivered','items':items})
    assert response.status_code == 422, response.text
    result = client.get('/api/v1/deliveries',headers=headers).json()['assignments'][0]
    assert result['stops'][0]['status'] == 'pending'


def test_partial_delivery_requires_reason_and_saves_each_quantity(integration):
    client, _, _, headers, *_ = integration
    assignment = assign(integration)
    link(integration, assignment)
    path = f"/api/v1/deliveries/{assignment['id']}/stops/STOP-1"
    body = {'status':'partial', 'items':[
        {'id':'MILK-ROW','delivered_quantity':'7.5'}, {'id':'BATTER-ROW','delivered_quantity':'1.25'},
    ]}
    assert client.post(path,headers=headers,json=body).status_code == 422
    body['reason'] = 'Customer accepted fewer goods'
    response = client.post(path,headers=headers,json=body)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['status'] == 'Closed with shortages'
    assert result['product_totals'][0]['delivered_quantity'] == '7.5'
    assert result['product_totals'][1]['delivered_quantity'] == '1.25'
    assert result['events'][0]['items'][0]['delivered_quantity'] == '7.5'
    assert client.post(path,headers=headers,json=body).json()['events'] == result['events']
    assert client.post(path,headers=headers,json=full_delivery()).status_code == 409
    assert routeos_app.delivery_integration.sync()['synced'] == 1
    evidence = json.loads(next(iter(integration[6].values()))['tracking_data'])
    assert evidence['stops'][0]['items'][1]['delivered_quantity'] == '1.25'


def test_manual_product_assignment_is_admin_only_and_locked_after_ride(integration):
    client, admin, _, headers, trip, *_ = integration
    trip['delivery_stops'][0]['delivery_note'] = None
    assignment = assign(integration)
    path = f"/api/v1/deliveries/{assignment['id']}/stops/STOP-1/products"
    body = {'items':[{'product_name':'Milk','planned_quantity':'10','uom':'L'},
                     {'product_name':'Batter','planned_quantity':'2','uom':'kg'}]}
    assert client.post(path,headers=headers,json=body).status_code == 403
    response = client.post(path,headers=admin,json=body)
    assert response.status_code == 200, response.text
    assert response.json()['stops'][0]['items'][1]['product_name'] == 'Batter'
    link(integration, assignment)
    assert client.post(path,headers=admin,json=body).status_code == 409


def test_erp_note_manifest_cannot_be_overridden(integration):
    client, admin, *_ = integration
    assignment = assign(integration)
    response = client.post(f"/api/v1/deliveries/{assignment['id']}/stops/STOP-1/products", headers=admin,
                           json={'items':[{'product_name':'Other','planned_quantity':'1','uom':'kg'}]})
    assert response.status_code == 409
