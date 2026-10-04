import sqlite3

import app as routeos_app

from conftest import api, auth_headers


def test_health_checks_database():
    with api() as client:
        response = client.get("/health")
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "ok"


def test_health_reports_database_failure(monkeypatch):
    with api() as client:
        def broken_connection():
            raise sqlite3.OperationalError("database unavailable")

        monkeypatch.setattr(routeos_app, "connection", broken_connection)
        response = client.get("/health")
        assert response.status_code == 503, response.text


def test_login_returns_token_for_seeded_admin():
    with api() as client:
        response = client.post(
            "/api/v1/auth/login", json={"name": "Sreekandan Nair"}
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["role"] == "admin"
        assert body["auth_token"], body


def test_duplicate_account_name_is_rejected():
    with api() as client:
        first = client.post("/api/v1/users", json={"name": "Duplicate Driver"})
        assert first.status_code == 201, first.text
        second = client.post("/api/v1/users", json={"name": "duplicate driver"})
        assert second.status_code == 409, second.text


def test_mutation_without_token_is_unauthorized():
    with api() as client:
        user = client.post("/api/v1/users", json={"name": "No Token Driver"}).json()
        response = client.post(
            "/api/v1/tracks",
            json={
                "recorder_id": user["id"],
                "organic_maps_track_id": "no-token-track",
                "points": [
                    {"latitude": 12.9716, "longitude": 77.5946},
                    {"latitude": 12.9720, "longitude": 77.5950},
                ],
            },
        )
        assert response.status_code == 401, response.text


def test_invalid_token_is_unauthorized():
    with api() as client:
        user = client.post("/api/v1/users", json={"name": "Bad Token Driver"}).json()
        response = client.post(
            "/api/v1/tracks",
            json={
                "recorder_id": user["id"],
                "organic_maps_track_id": "bad-token-track",
                "points": [
                    {"latitude": 12.9716, "longitude": 77.5946},
                    {"latitude": 12.9720, "longitude": 77.5950},
                ],
            },
            headers={"X-RouteOS-Token": "not-a-real-token"},
        )
        assert response.status_code == 401, response.text


def test_cross_driver_mutation_is_forbidden():
    with api() as client:
        alice = client.post("/api/v1/users", json={"name": "Alice Driver"}).json()
        bob = client.post("/api/v1/users", json={"name": "Bob Driver"}).json()
        response = client.post(
            "/api/v1/tracks",
            json={
                "recorder_id": alice["id"],
                "organic_maps_track_id": "spoofed-track",
                "points": [
                    {"latitude": 12.9716, "longitude": 77.5946},
                    {"latitude": 12.9720, "longitude": 77.5950},
                ],
            },
            headers=auth_headers(bob),
        )
        assert response.status_code == 403, response.text


def test_admin_endpoints_require_admin_role():
    with api() as client:
        driver = client.post("/api/v1/users", json={"name": "Plain Driver"}).json()
        admin = client.post(
            "/api/v1/auth/login", json={"name": "Sreekandan Nair"}
        ).json()
        forbidden = client.get("/api/v1/rides/active", headers=auth_headers(driver))
        assert forbidden.status_code == 403, forbidden.text
        allowed = client.get("/api/v1/rides/active", headers=auth_headers(admin))
        assert allowed.status_code == 200, allowed.text
        events_forbidden = client.get("/api/v1/events", headers=auth_headers(driver))
        assert events_forbidden.status_code == 403, events_forbidden.text
        events_allowed = client.get("/api/v1/events", headers=auth_headers(admin))
        assert events_allowed.status_code == 200, events_allowed.text
