import json
from contextlib import closing
from datetime import datetime

from app import connection, initialize_database

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
