import json
from contextlib import closing
from datetime import datetime

from app import connection, initialize_database

from conftest import api, auth_headers


def _user_and_track(client, name, points):
    user = client.post("/api/v1/users", json={"name": name}).json()
    response = client.post(
        "/api/v1/tracks",
        json={"recorder_id": user["id"], "organic_maps_track_id": "track-1", "points": points},
        headers=auth_headers(user),
    )
    assert response.status_code == 201, response.text
    return user, response.json()


def test_track_accepts_numeric_epoch_millis():
    with api() as client:
        _user_and_track(
            client,
            "Epoch Driver",
            [
                {"latitude": 12.9716, "longitude": 77.5946, "timestamp": 1759075200000},
                {"latitude": 12.9720, "longitude": 77.5950, "timestamp": 1759075800000},
            ],
        )


def test_track_accepts_iso_z_and_stores_utc_offset_form():
    with api() as client:
        _, created = _user_and_track(
            client,
            "Iso Driver",
            [
                {"latitude": 12.9716, "longitude": 77.5946, "timestamp": "2026-09-28T10:00:00.000Z"},
                {"latitude": 12.9720, "longitude": 77.5950, "timestamp": "2026-09-28T10:10:00.000Z"},
            ],
        )
        with closing(connection()) as db:
            row = db.execute(
                "SELECT points FROM recorded_tracks WHERE id = ?", (created["id"],)
            ).fetchone()
        stored = json.loads(row["points"])
        assert stored[0]["timestamp"] == "2026-09-28T10:00:00+00:00"
        assert datetime.fromisoformat(stored[0]["timestamp"]).tzinfo is not None


def test_track_accepts_offset_form_and_null_timestamp():
    with api() as client:
        _, created = _user_and_track(
            client,
            "Offset Driver",
            [
                {"latitude": 12.9716, "longitude": 77.5946, "timestamp": "2026-09-28T15:30:00+05:30"},
                {"latitude": 12.9720, "longitude": 77.5950, "timestamp": None},
            ],
        )
        with closing(connection()) as db:
            row = db.execute(
                "SELECT points FROM recorded_tracks WHERE id = ?", (created["id"],)
            ).fetchone()
        stored = json.loads(row["points"])
        assert stored[0]["timestamp"] == "2026-09-28T10:00:00+00:00"
        assert stored[1]["timestamp"] is None


def test_track_rejects_unparseable_timestamp():
    with api() as client:
        user = client.post("/api/v1/users", json={"name": "Bad Driver"}).json()
        response = client.post(
            "/api/v1/tracks",
            json={
                "recorder_id": user["id"],
                "organic_maps_track_id": "track-bad",
                "points": [
                    {"latitude": 12.9716, "longitude": 77.5946, "timestamp": "not-a-date"},
                    {"latitude": 12.9720, "longitude": 77.5950, "timestamp": "also-not-a-date"},
                ],
            },
            headers=auth_headers(user),
        )
        assert response.status_code == 201, response.text
        with closing(connection()) as db:
            row = db.execute(
                "SELECT points FROM recorded_tracks WHERE id = ?", (response.json()["id"],)
            ).fetchone()
        stored = json.loads(row["points"])
        assert all(point["timestamp"] is None for point in stored)
