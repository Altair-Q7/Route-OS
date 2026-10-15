"""
COVERAGE: live-ride location samples -- retries and out-of-order delivery keep the live marker correct.
"""
from datetime import datetime, timedelta, timezone
from contextlib import closing

import app as routeos_app
from conftest import api, auth_headers


def test_retried_and_out_of_order_samples_keep_live_marker_current(tmp_path, monkeypatch):
    monkeypatch.setattr(routeos_app, "DATABASE_PATH", tmp_path / "telemetry.db")
    with api() as client:
        user = client.post("/api/v1/users", json={"name": "Telemetry Driver"}).json()
        headers = auth_headers(user)
        route = client.post("/api/v1/planned-routes", headers=headers, json={
            "name": "Telemetry route", "distance_meters": 10000, "duration_seconds": 600,
            "points": [
                {"latitude": 10, "longitude": 77, "sequence": 0, "type": "start"},
                {"latitude": 10.1, "longitude": 77.1, "sequence": 1, "type": "destination"},
            ],
        }).json()
        ride = client.post("/api/v1/rides", headers=headers, json={
            "driver_id": user["id"], "route_id": route["id"], "vehicle_type": "car", "vehicle_number": "TEST"
        }).json()
        path = f"/api/v1/rides/{ride['id']}/locations"
        now = datetime.now(timezone.utc)
        current = {"driver_id": user["id"], "latitude": 10.1, "longitude": 77.1,
                   "sample_id": "current", "recorded_at": now.isoformat(), "accuracy_meters": 5}
        first = client.post(path, headers=headers, json=current)
        retry = client.post(path, headers=headers, json=current)
        assert first.status_code == retry.status_code == 201
        assert first.json()["id"] == retry.json()["id"]
        assert retry.json()["arrived"] is True
        old = {**current, "sample_id": "older", "recorded_at": (now - timedelta(minutes=10)).isoformat(),
               "latitude": 10, "longitude": 77}
        assert client.post(path, headers=headers, json=old).status_code == 201
        admin = client.post("/api/v1/auth/login", json={"name": "Sreekandan Nair"}).json()
        active = client.get("/api/v1/rides/active", headers=auth_headers(admin)).json()[0]
        assert active["latitude"] == 10.1
        assert active["accuracy_meters"] == 5
        assert active["location_stale"] is False
        with closing(routeos_app.connection()) as db:
            assert db.execute("SELECT COUNT(*) FROM live_locations WHERE ride_id=?", (ride["id"],)).fetchone()[0] == 2
        future = {**current, "sample_id": "future", "recorded_at": (now + timedelta(days=1)).isoformat()}
        assert client.post(path, headers=headers, json=future).status_code == 422
        assert client.post(path, headers=headers, json={**current, "recorded_at": "2026-10-05T12:00:00"}).status_code == 422
        client.post(f"/api/v1/rides/{ride['id']}/end", headers=headers, json={"driver_id": user["id"]})
        assert client.post(path, headers=headers, json=current).status_code == 409


def test_location_batch_is_atomic_deduplicated_and_updates_latest_marker(tmp_path, monkeypatch):
    monkeypatch.setattr(routeos_app, "DATABASE_PATH", tmp_path / "batch-telemetry.db")
    with api() as client:
        user = client.post("/api/v1/users", json={"name": "Batch Driver"}).json()
        headers = auth_headers(user)
        route = client.post("/api/v1/planned-routes", headers=headers, json={
            "name": "Batch route", "distance_meters": 1000, "duration_seconds": 120,
            "points": [
                {"latitude": 10, "longitude": 77, "sequence": 0, "type": "start"},
                {"latitude": 10.1, "longitude": 77.1, "sequence": 1, "type": "destination"},
            ],
        }).json()
        ride = client.post("/api/v1/rides", headers=headers, json={
            "driver_id": user["id"], "route_id": route["id"],
            "vehicle_type": "car", "vehicle_number": "BATCH",
        }).json()
        now = datetime.now(timezone.utc)
        locations = [
            {"driver_id": user["id"], "latitude": 10.1, "longitude": 77.1,
             "sample_id": "newest", "recorded_at": now.isoformat()},
            {"driver_id": user["id"], "latitude": 10.0, "longitude": 77.0,
             "sample_id": "older", "recorded_at": (now - timedelta(minutes=1)).isoformat()},
            {"driver_id": user["id"], "latitude": 10.1, "longitude": 77.1,
             "sample_id": "newest", "recorded_at": now.isoformat()},
        ]
        response = client.post(
            f"/api/v1/rides/{ride['id']}/locations/batch",
            headers=headers,
            json={"driver_id": user["id"], "locations": locations},
        )
        assert response.status_code == 201, response.text
        assert response.json()["accepted"] == 3
        assert response.json()["latest"]["sample_id"] == "newest"
        with closing(routeos_app.connection()) as db:
            assert db.execute(
                "SELECT COUNT(*) FROM live_locations WHERE ride_id=?", (ride["id"],)
            ).fetchone()[0] == 2
            latest = db.execute(
                "SELECT sample_id FROM latest_locations WHERE ride_id=?", (ride["id"],)
            ).fetchone()
            assert latest["sample_id"] == "newest"


def test_location_batch_rejects_mixed_driver_ids(tmp_path, monkeypatch):
    monkeypatch.setattr(routeos_app, "DATABASE_PATH", tmp_path / "mixed-batch.db")
    with api() as client:
        user = client.post("/api/v1/users", json={"name": "Mixed Batch Driver"}).json()
        response = client.post(
            "/api/v1/rides/1/locations/batch",
            headers=auth_headers(user),
            json={"driver_id": user["id"], "locations": [{
                "driver_id": user["id"] + 1, "latitude": 10, "longitude": 77,
            }]},
        )
        assert response.status_code == 422
