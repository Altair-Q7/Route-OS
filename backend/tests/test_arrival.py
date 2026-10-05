"""
COVERAGE: /rides/arrive -- destination vs start semantics and the fresh-GPS-location requirement.
"""
from contextlib import closing

import app as routeos_app
from conftest import api, auth_headers


def test_drawn_route_arrival_uses_destination_and_requires_fresh_location(tmp_path, monkeypatch):
    monkeypatch.setattr(routeos_app, "DATABASE_PATH", tmp_path / "arrival.db")
    with api() as client:
        user = client.post("/api/v1/users", json={"name": "Arrival Driver"}).json()
        headers = auth_headers(user)
        points = [
            {"latitude": 10, "longitude": 77, "sequence": 0, "type": "start"},
            {"latitude": 10.1, "longitude": 77.1, "sequence": 1, "type": "destination"},
        ]
        saved = client.post("/api/v1/planned-routes", headers=headers, json={
            "name": "Arrival route", "points": points, "distance_meters": 15000, "duration_seconds": 900
        }).json()
        route = client.get(f"/api/v1/routes/{saved['id']}", headers=headers).json()
        assert route["start_latitude"] == route["hub_latitude"] == 10
        assert route["destination_latitude"] == 10.1
        ride = client.post("/api/v1/rides", headers=headers, json={
            "driver_id": user["id"], "route_id": route["id"], "vehicle_type": "car", "vehicle_number": "TEST"
        }).json()
        path = f"/api/v1/rides/{ride['id']}"
        location = {"driver_id": user["id"], "latitude": 10, "longitude": 77}
        assert client.post(path + "/locations", json=location, headers=headers).json()["arrived"] is False
        assert client.post(path + "/arrive", json={"driver_id": user["id"]}, headers=headers).status_code == 409
        location.update(latitude=10.1, longitude=77.1)
        assert client.post(path + "/locations", json=location, headers=headers).json()["arrived"] is True
        with closing(routeos_app.connection()) as db, db:
            db.execute("UPDATE live_locations SET recorded_at='2000-01-01T00:00:00+00:00' WHERE ride_id=?", (ride["id"],))
        assert client.post(path + "/arrive", json={"driver_id": user["id"]}, headers=headers).status_code == 409
        client.post(path + "/locations", json=location, headers=headers)
        result = client.post(path + "/arrive", json={"driver_id": user["id"]}, headers=headers)
        assert result.status_code == 200, result.text
        assert result.json()["distance_to_destination_m"] == 0
