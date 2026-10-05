import sqlite3
from contextlib import closing

import pytest

import app as routeos_app

from conftest import api, auth_headers


@pytest.mark.parametrize("has_route_type", [False, True])
def test_legacy_routes_schema_is_migrated_before_indexes(tmp_path, monkeypatch, has_route_type):
    database = tmp_path / "legacy.db"
    monkeypatch.setattr(routeos_app, "DATABASE_PATH", database)
    with sqlite3.connect(database) as db:
        db.executescript(
            """
            CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL);
            INSERT INTO users VALUES (42, 'Legacy owner', '2026-09-01T00:00:00+00:00');
            CREATE TABLE recorded_tracks (
              id INTEGER PRIMARY KEY, recorder_id INTEGER NOT NULL,
              organic_maps_track_id TEXT, points TEXT NOT NULL, created_at TEXT NOT NULL
            );
            INSERT INTO recorded_tracks VALUES (
              43, 42, 'legacy-track',
              '[{"latitude": 10, "longitude": 77}, {"latitude": 11, "longitude": 77}]',
              '2026-09-01T00:00:00+00:00'
            );
            """
        )
        route_type_column = "route_type TEXT NOT NULL DEFAULT 'recorded'," if has_route_type else ""
        db.execute(
            f"""
            CREATE TABLE routes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              recorder_id INTEGER NOT NULL,
              track_id INTEGER NOT NULL,
              origin TEXT,
              destination TEXT,
              {route_type_column}
              created_at TEXT NOT NULL
            )
            """
        )
        db.execute(
            "INSERT INTO routes(id, name, recorder_id, track_id, created_at) VALUES (44, 'Legacy route', 42, 43, ?)",
            ("2026-09-01T00:00:00+00:00",),
        )

    routeos_app.initialize_database()
    routeos_app.initialize_database()

    with closing(routeos_app.connection()) as db:
        columns = {row["name"] for row in db.execute("PRAGMA table_info(routes)")}
        assert "deleted_at" in columns
        assert db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='index' AND name='idx_routes_deleted_created'"
        ).fetchone()
        route = db.execute("SELECT * FROM routes WHERE id=44").fetchone()
        assert route["name"] == "Legacy route"
        assert route["track_id"] == 43
        assert route["point_count"] == 2
        assert route["route_type"] == "recorded"


def test_seeded_password_and_sessions_survive_restart(tmp_path, monkeypatch):
    database = tmp_path / "production.db"
    monkeypatch.setattr(routeos_app, "DATABASE_PATH", database)
    monkeypatch.setenv("ROUTEOS_DEVELOPMENT_AUTH", "0")
    routeos_app.initialize_database()

    with pytest.raises(routeos_app.HTTPException) as error:
        routeos_app.login(routeos_app.LoginIn(name="D.B Cooper", password="Demo123Demo"))
    assert error.value.status_code == 401

    password = "a provisioned password"
    with closing(routeos_app.connection()) as db, db:
        user = db.execute("SELECT id FROM users WHERE name = 'D.B Cooper'").fetchone()
        db.execute(
            "UPDATE users SET password_hash=? WHERE id=?",
            (routeos_app.password_hash(password), user["id"]),
        )

    session = routeos_app.login(routeos_app.LoginIn(name="D.B Cooper", password=password))
    routeos_app.initialize_database()

    assert routeos_app.login(routeos_app.LoginIn(name="D.B Cooper", password=password))["id"] == session["id"]
    assert routeos_app.current_user(None, "Bearer " + session["auth_token"])["id"] == session["id"]
    with pytest.raises(routeos_app.HTTPException) as error:
        routeos_app.login(routeos_app.LoginIn(name="D.B Cooper", password="Demo123Demo"))
    assert error.value.status_code == 401


@pytest.mark.parametrize("header", ["Authorization", "X-RouteOS-Token"])
def test_development_logout_revokes_quick_login_token(tmp_path, monkeypatch, header):
    database = tmp_path / "development.db"
    monkeypatch.setattr(routeos_app, "DATABASE_PATH", database)
    monkeypatch.setenv("ROUTEOS_DEVELOPMENT_AUTH", "1")
    with api() as client:
        user = client.post("/api/v1/auth/login", json={"name": "D.B Cooper"}).json()
        token = user["auth_token"]
        headers = {header: "Bearer " + token if header == "Authorization" else token}
        assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
        assert client.get("/api/v1/routes", headers=headers).status_code == 401
        fresh_user = client.post("/api/v1/auth/login", json={"name": "D.B Cooper"}).json()
        assert fresh_user["auth_token"] != token
        assert client.get("/api/v1/routes", headers=auth_headers(fresh_user)).status_code == 200


def test_blank_route_names_are_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(routeos_app, "DATABASE_PATH", tmp_path / "validation.db")
    with api() as client:
        user = client.post("/api/v1/users", json={"name": "Blank Name Driver"}).json()
        response = client.post(
            "/api/v1/tracks",
            json={
                "recorder_id": user["id"],
                "points": [
                    {"latitude": 12.9716, "longitude": 77.5946},
                    {"latitude": 12.9720, "longitude": 77.5950},
                ],
            },
            headers=auth_headers(user),
        )
        track = response.json()
        route = client.post(
            "/api/v1/routes",
            json={"name": "   ", "recorder_id": user["id"], "track_id": track["id"]},
            headers=auth_headers(user),
        )
        assert route.status_code == 422
        route = client.post(
            "/api/v1/routes",
            json={"name": "  Named route  ", "recorder_id": user["id"], "track_id": track["id"]},
            headers=auth_headers(user),
        )
        assert route.status_code == 201
        assert route.json()["name"] == "Named route"
        route_id = route.json()["id"]
        renamed = client.patch(
            f"/api/v1/routes/{route_id}",
            json={"name": "   ", "driver_id": user["id"]},
            headers=auth_headers(user),
        )
        assert renamed.status_code == 422
        assert client.get(f"/api/v1/routes/{route_id}", headers=auth_headers(user)).json()["name"] == "Named route"


@pytest.mark.parametrize("field", ["vehicle_type", "vehicle_number"])
def test_blank_vehicle_details_are_rejected(tmp_path, monkeypatch, field):
    monkeypatch.setattr(routeos_app, "DATABASE_PATH", tmp_path / "vehicle.db")
    with api() as client:
        user = client.post("/api/v1/users", json={"name": "Vehicle Driver"}).json()
        response = client.post(
            "/api/v1/rides",
            json={"driver_id": user["id"], "route_id": 1, "vehicle_type": "car", "vehicle_number": "TEST", field: "   "},
            headers=auth_headers(user),
        )
        assert response.status_code == 422
