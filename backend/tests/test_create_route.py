"""
COVERAGE: creating tracks + shared routes end to end (recorded vs drawn route types).
"""
import json
from contextlib import closing
from datetime import datetime

from app import connection, initialize_database
import app as routeos_app

from conftest import api, auth_headers


def _create_route(client, name, route_type):
    user = client.post("/api/v1/users", json={"name": f"{name} driver"}).json()
    headers = auth_headers(user)
    track = client.post(
        "/api/v1/tracks",
        json={
            "recorder_id": user["id"],
            "organic_maps_track_id": f"{name}-track",
            "points": [
                {"latitude": 12.9716, "longitude": 77.5946, "timestamp": "2026-09-28T10:00:00Z"},
                {"latitude": 12.9720, "longitude": 77.5950, "timestamp": "2026-09-28T10:10:00Z"},
            ],
        },
        headers=headers,
    ).json()
    response = client.post(
        "/api/v1/routes",
        json={
            "name": name,
            "recorder_id": user["id"],
            "track_id": track["id"],
            "origin": "Hub",
            "destination": "Depot",
            "route_type": route_type,
            "hub_latitude": 12.9716,
            "hub_longitude": 77.5946,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return user, response.json()


def test_create_route_keeps_route_type_and_created_at_in_their_columns():
    with api() as client:
        _, created = _create_route(client, "Drawn route", "drawn")
        with closing(connection()) as db:
            row = db.execute("SELECT route_type, created_at FROM routes WHERE id = ?", (created["id"],)).fetchone()
        assert row["route_type"] == "drawn"
        assert datetime.fromisoformat(row["created_at"]) is not None
        assert created["route_type"] == "drawn"


def test_create_recorded_route_stores_recorded_type():
    with api() as client:
        _, created = _create_route(client, "Recorded route", "recorded")
        with closing(connection()) as db:
            row = db.execute("SELECT route_type, created_at FROM routes WHERE id = ?", (created["id"],)).fetchone()
        assert row["route_type"] == "recorded"


def test_listed_routes_keep_route_type_and_created_at_in_their_columns():
    with api() as client:
        user, created = _create_route(client, "Filtered route", "drawn")
        listed = client.get("/api/v1/routes", headers=auth_headers(user)).json()
        assert created["id"] in [route["id"] for route in listed]
        for route in listed:
            assert route["route_type"] in {"recorded", "drawn"}
            datetime.fromisoformat(route["created_at"])


def test_get_route_uses_persisted_stats_for_recorded_tracks(monkeypatch):
    with api() as client:
        user, created = _create_route(client, "Cached stats route", "recorded")

        def unexpected_recalculation(_points):
            raise AssertionError("recorded route stats should be read from the database")

        monkeypatch.setattr(routeos_app, "route_stats", unexpected_recalculation)
        response = client.get(f"/api/v1/routes/{created['id']}", headers=auth_headers(user))

        assert response.status_code == 200, response.text
        route = response.json()
        assert route["point_count"] == 2
        assert route["distance_meters"] > 0
        assert route["duration_seconds"] == 600
        assert "saved_distance" not in route
        assert "saved_duration" not in route


def test_recorded_route_preview_is_bounded_and_preserves_endpoints():
    with api() as client:
        user = client.post("/api/v1/users", json={"name": "Preview Driver"}).json()
        headers = auth_headers(user)
        points = [
            {
                "latitude": 10 + index / 100_000,
                "longitude": 77 + index / 100_000,
                "timestamp": f"2026-01-01T00:{index // 60:02d}:{index % 60:02d}Z",
            }
            for index in range(120)
        ]
        track = client.post("/api/v1/tracks", headers=headers, json={
            "recorder_id": user["id"], "points": points,
        }).json()
        route = client.post("/api/v1/routes", headers=headers, json={
            "name": "Preview route", "recorder_id": user["id"], "track_id": track["id"],
            "route_type": "recorded",
        }).json()

        preview = client.get(
            f"/api/v1/routes/{route['id']}?max_points=10", headers=headers
        ).json()
        assert preview["point_count"] == len(points)
        assert len(preview["points"]) == 10
        assert preview["points"][0]["latitude"] == points[0]["latitude"]
        assert preview["points"][-1]["latitude"] == points[-1]["latitude"]

        full = client.get(f"/api/v1/routes/{route['id']}", headers=headers).json()
        assert len(full["points"]) == len(points)


def test_initialize_database_repairs_swapped_columns():
    with api() as client:
        _, created = _create_route(client, "Corrupted route", "drawn")
        with closing(connection()) as db:
            db.execute(
                "UPDATE routes SET route_type = created_at, created_at = route_type WHERE id = ?",
                (created["id"],),
            )
            db.commit()
        initialize_database()
        with closing(connection()) as db:
            row = db.execute("SELECT route_type, created_at FROM routes WHERE id = ?", (created["id"],)).fetchone()
        assert row["route_type"] == "drawn"
        datetime.fromisoformat(row["created_at"])
        initialize_database()
        with closing(connection()) as db:
            row = db.execute("SELECT route_type, created_at FROM routes WHERE id = ?", (created["id"],)).fetchone()
        assert row["route_type"] == "drawn"
        datetime.fromisoformat(row["created_at"])
