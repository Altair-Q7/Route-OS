"""
COVERAGE: custom event permissions -- admin only, reserved kinds rejected, payload size limits, actor spoofing blocked.
"""
import pytest

import app as routeos_app
from conftest import api, auth_headers


def test_custom_events_require_admin_and_cannot_spoof_server_actions(tmp_path, monkeypatch):
    monkeypatch.setattr(routeos_app, "DATABASE_PATH", tmp_path / "events.db")
    with api() as client:
        driver = client.post("/api/v1/auth/login", json={"name": "D.B Cooper"}).json()
        admin = client.post("/api/v1/auth/login", json={"name": "Sreekandan Nair"}).json()
        assert client.post("/api/v1/events", headers=auth_headers(driver), json={"kind": "note"}).status_code == 403
        for kind in ("ride_ended", "ride_arrived", "route_shared", "   "):
            assert client.post("/api/v1/events", headers=auth_headers(admin), json={"kind": kind}).status_code == 422
        event = client.post("/api/v1/events", headers=auth_headers(admin),
                            json={"kind": "note", "payload": {"actor_id": driver["id"]}})
        assert event.status_code == 201
        assert event.json()["payload"]["actor_id"] == admin["id"]
        assert client.post("/api/v1/events", headers=auth_headers(admin),
                           json={"kind": "note", "payload": {"text": "x" * 16_384}}).status_code == 422


@pytest.mark.parametrize("model,fields", [
    (routeos_app.PlannedRouteIn, {"name": "Route", "points": [
        {"latitude": 10, "longitude": 77, "sequence": 0, "type": "start"},
        {"latitude": 11, "longitude": 77, "sequence": 1, "type": "destination"},
    ], "distance_meters": float("inf"), "duration_seconds": 60}),
    (routeos_app.LiveLocationIn, {"driver_id": 1, "latitude": 10, "longitude": 77, "speed_mps": float("inf")}),
    (routeos_app.TrackPoint, {"latitude": 10, "longitude": 77, "altitude_meters": float("inf")}),
])
def test_non_finite_measurements_are_rejected(model, fields):
    with pytest.raises(ValueError):
        model(**fields)
