from conftest import api, auth_headers


POINTS = [
    {"latitude": 12.9716, "longitude": 77.5946, "timestamp": "2026-09-28T10:00:00Z"},
    {"latitude": 12.9920, "longitude": 77.6150, "timestamp": "2026-09-28T10:10:00Z"},
]


def _driver(client, name):
    user = client.post("/api/v1/users", json={"name": name}).json()
    assert "auth_token" in user, user
    return user, auth_headers(user)


def _route(client, user, headers, name="Ride route", hub=None):
    track = client.post(
        "/api/v1/tracks",
        json={"recorder_id": user["id"], "organic_maps_track_id": f"{name}-track", "points": POINTS},
        headers=headers,
    ).json()
    body = {
        "name": name,
        "recorder_id": user["id"],
        "track_id": track["id"],
        "origin": "Hub",
        "destination": "Depot",
        "route_type": "recorded",
    }
    if hub is not None:
        body["hub_latitude"], body["hub_longitude"] = hub
    route = client.post("/api/v1/routes", json=body, headers=headers)
    assert route.status_code == 201, route.text
    return route.json()


def _start(client, user, headers, route_id):
    return client.post(
        "/api/v1/rides",
        json={
            "driver_id": user["id"],
            "route_id": route_id,
            "vehicle_type": "auto",
            "vehicle_number": "KL-01-AB-1234",
        },
        headers=headers,
    )


def _locate(client, user, headers, ride_id, lat, lon):
    return client.post(
        f"/api/v1/rides/{ride_id}/locations",
        json={"driver_id": user["id"], "latitude": lat, "longitude": lon},
        headers=headers,
    )


def test_double_start_returns_409():
    with api() as client:
        user, headers = _driver(client, "Double Start Driver")
        route = _route(client, user, headers)
        assert _start(client, user, headers, route["id"]).status_code == 201
        second = _start(client, user, headers, route["id"])
        assert second.status_code == 409, second.text


def test_end_is_idempotent_and_keeps_first_ended_at():
    with api() as client:
        user, headers = _driver(client, "Idempotent Driver")
        route = _route(client, user, headers)
        ride = _start(client, user, headers, route["id"]).json()
        first = client.post(
            f"/api/v1/rides/{ride['id']}/end", json={"driver_id": user["id"]}, headers=headers
        )
        assert first.status_code == 200, first.text
        second = client.post(
            f"/api/v1/rides/{ride['id']}/end", json={"driver_id": user["id"]}, headers=headers
        )
        assert second.status_code == 200, second.text
        assert second.json()["ended_at"] == first.json()["ended_at"]
        assert second.json()["status"] == "ended"


def test_end_other_drivers_ride_is_forbidden():
    with api() as client:
        owner, owner_headers = _driver(client, "Ride Owner")
        intruder, intruder_headers = _driver(client, "Ride Intruder")
        route = _route(client, owner, owner_headers)
        ride = _start(client, owner, owner_headers, route["id"]).json()
        response = client.post(
            f"/api/v1/rides/{ride['id']}/end",
            json={"driver_id": intruder["id"]},
            headers=intruder_headers,
        )
        assert response.status_code == 403, response.text


def test_end_without_token_is_unauthorized():
    with api() as client:
        user, headers = _driver(client, "Tokenless Ender")
        route = _route(client, user, headers)
        ride = _start(client, user, headers, route["id"]).json()
        response = client.post(f"/api/v1/rides/{ride['id']}/end", json={"driver_id": user["id"]})
        assert response.status_code == 401, response.text


def test_location_after_end_is_rejected():
    with api() as client:
        user, headers = _driver(client, "Late Locator")
        route = _route(client, user, headers)
        ride = _start(client, user, headers, route["id"]).json()
        client.post(
            f"/api/v1/rides/{ride['id']}/end", json={"driver_id": user["id"]}, headers=headers
        )
        late = _locate(client, user, headers, ride["id"], 12.9716, 77.5946)
        assert late.status_code == 409, late.text


def test_location_reports_hub_proximity():
    with api() as client:
        user, headers = _driver(client, "Proximity Driver")
        route = _route(client, user, headers, hub=(12.9716, 77.5946))
        ride = _start(client, user, headers, route["id"]).json()
        at_hub = _locate(client, user, headers, ride["id"], 12.9716, 77.5946)
        assert at_hub.status_code == 201, at_hub.text
        assert at_hub.json()["arrived"] is False
        assert at_hub.json()["distance_to_hub_m"] == 0.0
        destination = _locate(client, user, headers, ride["id"], 12.9920, 77.6150)
        assert destination.json()["arrived"] is True
        assert destination.json()["distance_to_destination_m"] == 0.0
        far = _locate(client, user, headers, ride["id"], 13.5, 78.0)
        assert far.status_code == 201, far.text
        assert far.json()["arrived"] is False
        assert far.json()["distance_to_hub_m"] > 1000


def test_arrive_at_destination_ends_ride_and_logs_event():
    with api() as client:
        user, headers = _driver(client, "Arriving Driver")
        route = _route(client, user, headers, hub=(12.9716, 77.5946))
        ride = _start(client, user, headers, route["id"]).json()
        _locate(client, user, headers, ride["id"], 12.9920, 77.6150)
        arrived = client.post(
            f"/api/v1/rides/{ride['id']}/arrive",
            json={"driver_id": user["id"]},
            headers=headers,
        )
        assert arrived.status_code == 200, arrived.text
        body = arrived.json()
        assert body["status"] == "ended"
        assert body["arrived"] is True
        active = client.get(
            f"/api/v1/drivers/{user['id']}/active-ride", headers=headers
        )
        assert active.status_code == 404, active.text


def test_arrive_far_from_hub_is_rejected():
    with api() as client:
        user, headers = _driver(client, "Far Driver")
        route = _route(client, user, headers, hub=(12.9716, 77.5946))
        ride = _start(client, user, headers, route["id"]).json()
        _locate(client, user, headers, ride["id"], 13.5, 78.0)
        response = client.post(
            f"/api/v1/rides/{ride['id']}/arrive",
            json={"driver_id": user["id"]},
            headers=headers,
        )
        assert response.status_code == 409, response.text


def test_arrive_requires_location_but_explicit_end_allows_manual_completion():
    with api() as client:
        user, headers = _driver(client, "Manual Arrival Driver")
        route = _route(client, user, headers)
        ride = _start(client, user, headers, route["id"]).json()
        response = client.post(
            f"/api/v1/rides/{ride['id']}/arrive",
            json={"driver_id": user["id"]},
            headers=headers,
        )
        assert response.status_code == 409, response.text
        response = client.post(
            f"/api/v1/rides/{ride['id']}/end", json={"driver_id": user["id"]}, headers=headers
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "ended"
