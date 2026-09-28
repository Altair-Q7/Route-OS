import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone

import pytest

from app import connection, initialize_database

from conftest import api, auth_headers


def test_foreign_keys_are_enforced():
    with closing(connection()) as db:
        assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO rides(driver_id, route_id, vehicle_type, vehicle_number, status, started_at)"
                " VALUES (999001, 999002, 'auto', 'X', 'active', '2026-09-28T10:00:00+00:00')"
            )


def test_delete_route_cascades_favorites_and_recents():
    with api() as client:
        user = client.post("/api/v1/users", json={"name": "Cascade Driver"}).json()
        headers = auth_headers(user)
        track = client.post(
            "/api/v1/tracks",
            json={
                "recorder_id": user["id"],
                "organic_maps_track_id": "cascade-track",
                "points": [
                    {"latitude": 12.9716, "longitude": 77.5946},
                    {"latitude": 12.9720, "longitude": 77.5950},
                ],
            },
            headers=headers,
        ).json()
        route = client.post(
            "/api/v1/routes",
            json={
                "name": "Cascade route",
                "recorder_id": user["id"],
                "track_id": track["id"],
            },
            headers=headers,
        ).json()
        assert client.post(
            f"/api/v1/routes/{route['id']}/favorite",
            json={"driver_id": user["id"]},
            headers=headers,
        ).status_code == 200
        assert client.post(
            f"/api/v1/routes/{route['id']}/recent",
            json={"driver_id": user["id"]},
            headers=headers,
        ).status_code == 200
        deleted = client.delete(
            f"/api/v1/routes/{route['id']}?driver_id={user['id']}", headers=headers
        )
        assert deleted.status_code == 200, deleted.text
        with closing(connection()) as db:
            assert db.execute(
                "SELECT 1 FROM route_favorites WHERE route_id = ?", (route["id"],)
            ).fetchone() is None
            assert db.execute(
                "SELECT 1 FROM route_recents WHERE route_id = ?", (route["id"],)
            ).fetchone() is None


def test_startup_cleans_orphaned_rows():
    with closing(connection()) as db:
        db.execute("PRAGMA foreign_keys = OFF")
        db.execute(
            "INSERT INTO route_favorites(user_id, route_id, created_at) VALUES (999003, 999004, '2026-09-28T10:00:00+00:00')"
        )
        db.commit()
    initialize_database()
    with closing(connection()) as db:
        assert db.execute(
            "SELECT 1 FROM route_favorites WHERE user_id = 999003"
        ).fetchone() is None


def test_routes_list_orders_by_created_at_descending():
    with api() as client:
        user = client.post("/api/v1/users", json={"name": "Ordering Driver"}).json()
        headers = auth_headers(user)
        points = [
            {"latitude": 12.9716, "longitude": 77.5946},
            {"latitude": 12.9720, "longitude": 77.5950},
        ]
        first_id = client.post(
            "/api/v1/routes",
            json={
                "name": "Ordering route A",
                "recorder_id": user["id"],
                "track_id": client.post(
                    "/api/v1/tracks",
                    json={"recorder_id": user["id"], "points": points},
                    headers=headers,
                ).json()["id"],
            },
            headers=headers,
        ).json()["id"]
        second_id = client.post(
            "/api/v1/routes",
            json={
                "name": "Ordering route B",
                "recorder_id": user["id"],
                "track_id": client.post(
                    "/api/v1/tracks",
                    json={"recorder_id": user["id"], "points": points},
                    headers=headers,
                ).json()["id"],
            },
            headers=headers,
        ).json()["id"]
        backdated = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        with closing(connection()) as db:
            db.execute("UPDATE routes SET created_at = ? WHERE id = ?", (backdated, second_id))
            db.commit()
        listed = client.get("/api/v1/routes").json()
        positions = {route["id"]: index for index, route in enumerate(listed)}
        assert positions[first_id] < positions[second_id]
