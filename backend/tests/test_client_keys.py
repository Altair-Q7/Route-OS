"""Client API keys survive restarts and can be revoked without a redeploy."""
from contextlib import closing

import pytest

from conftest import api, auth_headers, routeos_app


@pytest.fixture
def keys(monkeypatch, tmp_path):
    monkeypatch.setattr(routeos_app, "DATABASE_PATH", tmp_path / "keys.db")
    monkeypatch.delenv("ROUTEOS_CLIENT_API_KEY", raising=False)
    with api() as client:
        admin = client.post("/api/v1/auth/login", json={"name": "Sreekandan Nair"}).json()
        driver = client.post("/api/v1/auth/login", json={"name": "D.B Cooper"}).json()
        yield client, auth_headers(admin), auth_headers(driver)


def issue(client, admin, label="Saravana reporting", **body):
    response = client.post("/api/v1/client-keys", headers=admin,
                           json={"label": label, **body})
    assert response.status_code == 201, response.text
    return response.json()


def test_an_issued_key_reads_deliveries(keys):
    client, admin, _ = keys
    key = issue(client, admin)["key"]
    result = client.get("/api/v1/client/deliveries", headers={"X-RouteOS-Client-Key": key})
    assert result.status_code == 200, result.text
    assert result.json() == {"trips": [], "count": 0}


def test_the_key_is_shown_once_and_only_a_hash_is_kept(keys):
    client, admin, _ = keys
    issued = issue(client, admin)
    assert issued["key"] and "shown once" in issued["warning"]
    listed = client.get("/api/v1/client-keys", headers=admin).json()["keys"]
    assert "key" not in listed[0] and "token_hash" not in listed[0]
    assert listed[0]["label"] == "Saravana reporting"


def test_a_key_survives_a_restart(keys, monkeypatch, tmp_path):
    client, admin, _ = keys
    key = issue(client, admin)["key"]
    # A restart is a new app over the same database file.
    monkeypatch.setattr(routeos_app, "DATABASE_PATH", tmp_path / "keys.db")
    with api() as restarted:
        assert restarted.get("/api/v1/client/deliveries",
                             headers={"X-RouteOS-Client-Key": key}).status_code == 200


def test_revoking_a_key_stops_it_immediately(keys):
    client, admin, _ = keys
    key = issue(client, admin)["key"]
    headers = {"X-RouteOS-Client-Key": key}
    assert client.get("/api/v1/client/deliveries", headers=headers).status_code == 200

    key_id = client.get("/api/v1/client-keys", headers=admin).json()["keys"][0]["id"]
    revoked = client.delete(f"/api/v1/client-keys/{key_id}", headers=admin)
    assert revoked.status_code == 200 and revoked.json() == {"revoked": key_id}
    assert client.get("/api/v1/client/deliveries", headers=headers).status_code == 401
    # Revoking twice is reported rather than silently succeeding.
    assert client.delete(f"/api/v1/client-keys/{key_id}", headers=admin).status_code == 404


def test_an_expired_key_is_refused(keys):
    client, admin, _ = keys
    with closing(routeos_app.connection()) as db:
        db.execute("UPDATE client_keys SET expires_at='2000-01-01T00:00:00+00:00'")
        db.commit()
    key = issue(client, admin, label="Old key")["key"]
    with closing(routeos_app.connection()) as db:
        rows = db.execute("SELECT id,label FROM client_keys").fetchall()
        expired = next(row["id"] for row in rows if row["label"] == "Old key")
        db.execute("UPDATE client_keys SET expires_at='2000-01-01T00:00:00+00:00' WHERE id=?", (expired,))
        db.commit()
    assert client.get("/api/v1/client/deliveries",
                      headers={"X-RouteOS-Client-Key": key}).status_code == 401


def test_several_keys_can_coexist_so_one_can_be_rotated(keys):
    client, admin, _ = keys
    old = issue(client, admin, label="Old")["key"]
    new = issue(client, admin, label="New")["key"]
    assert old != new
    for key in (old, new):
        assert client.get("/api/v1/client/deliveries",
                          headers={"X-RouteOS-Client-Key": key}).status_code == 200

    old_id = next(row["id"] for row in client.get("/api/v1/client-keys", headers=admin).json()["keys"]
                  if row["label"] == "Old")
    client.delete(f"/api/v1/client-keys/{old_id}", headers=admin)
    # Swapping the key does not interrupt the customer's polling.
    assert client.get("/api/v1/client/deliveries",
                      headers={"X-RouteOS-Client-Key": old}).status_code == 401
    assert client.get("/api/v1/client/deliveries",
                      headers={"X-RouteOS-Client-Key": new}).status_code == 200


def test_only_an_admin_manages_keys(keys):
    client, admin, driver = keys
    assert client.get("/api/v1/client-keys", headers=driver).status_code == 403
    assert client.post("/api/v1/client-keys", headers=driver,
                       json={"label": "Sneaky"}).status_code == 403
    assert client.get("/api/v1/client-keys").status_code == 401
    assert client.delete("/api/v1/client-keys/1", headers=driver).status_code == 403


def test_a_key_still_cannot_change_anything(keys):
    client, admin, _ = keys
    key = issue(client, admin)["key"]
    headers = {"X-RouteOS-Client-Key": key}
    # Read-only: creating a trip or confirming a delivery is refused.
    assert client.post("/api/v1/deliveries/trips", headers=headers, json={"trip": "x"}).status_code == 401
    assert client.post("/api/v1/supermarkets", headers=headers,
                       json={"name": "Sneaky", "latitude": 1, "longitude": 1}).status_code == 401
    assert client.get("/api/v1/deliveries", headers=headers).status_code == 401


def test_an_unnamed_key_is_rejected(keys):
    client, admin, _ = keys
    assert client.post("/api/v1/client-keys", headers=admin, json={"label": "   "}).status_code == 422
    assert client.post("/api/v1/client-keys", headers=admin,
                       json={"label": "x", "expires_in_days": 0}).status_code == 422
