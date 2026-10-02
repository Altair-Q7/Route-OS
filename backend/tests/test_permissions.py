from conftest import api, auth_headers


POINTS = [
    {"latitude": 12.9716, "longitude": 77.5946},
    {"latitude": 12.9720, "longitude": 77.5950},
]


def _route(client, owner, headers, name="Permission route"):
    track = client.post(
        "/api/v1/tracks",
        json={"recorder_id": owner["id"], "points": POINTS},
        headers=headers,
    ).json()
    response = client.post(
        "/api/v1/routes",
        json={"name": name, "recorder_id": owner["id"], "track_id": track["id"]},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_route_reads_require_authentication():
    with api() as client:
        response = client.get("/api/v1/routes")
        assert response.status_code == 401
        response = client.get("/api/v1/routes/1")
        assert response.status_code == 401


def test_route_list_cannot_be_personalized_for_another_driver():
    with api() as client:
        first = client.post("/api/v1/users", json={"name": "List Owner"}).json()
        second = client.post("/api/v1/users", json={"name": "List Viewer"}).json()
        response = client.get(
            f"/api/v1/routes?driver_id={first['id']}", headers=auth_headers(second)
        )
        assert response.status_code == 403


def test_only_route_owner_or_admin_can_share():
    with api() as client:
        owner = client.post("/api/v1/users", json={"name": "Share Owner"}).json()
        other = client.post("/api/v1/users", json={"name": "Share Other"}).json()
        route = _route(client, owner, auth_headers(owner))
        response = client.post(
            f"/api/v1/routes/{route['id']}/share",
            json={"driver_id": other["id"]},
            headers=auth_headers(other),
        )
        assert response.status_code == 403


def test_admin_can_end_another_driver_ride():
    with api() as client:
        driver = client.post("/api/v1/users", json={"name": "Active Driver"}).json()
        admin = client.post(
            "/api/v1/auth/login", json={"name": "Thomachan Valiparambil"}
        ).json()
        route = _route(client, driver, auth_headers(driver))
        ride = client.post(
            "/api/v1/rides",
            json={
                "driver_id": driver["id"],
                "route_id": route["id"],
                "vehicle_type": "car",
                "vehicle_number": "KL-01-BETA",
            },
            headers=auth_headers(driver),
        ).json()
        response = client.post(
            f"/api/v1/rides/{ride['id']}/end",
            json={"driver_id": driver["id"]},
            headers=auth_headers(admin),
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "ended"
        listing = client.get('/api/v1/routes', headers=auth_headers(driver)).json()
        assert next(r for r in listing if r['id'] == route['id'])['last_used_at'] is not None
        cleared = client.delete(f"/api/v1/routes/{route['id']}/recent?driver_id={driver['id']}", headers=auth_headers(driver))
        assert cleared.status_code == 200
        assert client.get(f"/api/v1/routes/{route['id']}", headers=auth_headers(driver)).status_code == 200
