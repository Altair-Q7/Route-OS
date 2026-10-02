from conftest import api, auth_headers


def test_planned_route_round_trip_preserves_order_and_native_statistics():
    with api() as client:
        owner = client.post('/api/v1/users', json={'name': 'Planner owner'}).json()
        headers = auth_headers(owner)
        points = [{'latitude': 10.1 + i / 100, 'longitude': 77.1, 'sequence': i,
                   'type': 'start' if i == 0 else 'destination' if i == 3 else 'via',
                   'label': f'Point {i}'} for i in range(4)]
        response = client.post('/api/v1/planned-routes', json={'name': 'Multi-stop', 'points': points,
                               'distance_meters': 18400, 'duration_seconds': 3100}, headers=headers)
        assert response.status_code == 201, response.text
        route = client.get(f"/api/v1/routes/{response.json()['id']}", headers=headers).json()
        assert [p['sequence'] for p in route['points']] == [0, 1, 2, 3]
        assert route['points'][1]['type'] == 'via'
        assert route['distance_meters'] == 18400
        assert route['duration_seconds'] == 3100
        other = client.post('/api/v1/users', json={'name': 'Planner viewer'}).json()
        assert client.get(f"/api/v1/routes/{route['id']}", headers=auth_headers(other)).status_code == 200
        assert client.delete(f"/api/v1/routes/{route['id']}?driver_id={other['id']}", headers=auth_headers(other)).status_code == 403


def test_invalid_planner_order_is_rejected():
    with api() as client:
        user = client.post('/api/v1/users', json={'name': 'Invalid planner'}).json()
        points = [{'latitude': 10, 'longitude': 77, 'sequence': i, 'type': 'via'} for i in range(2)]
        response = client.post('/api/v1/planned-routes', json={'name': 'Invalid', 'points': points,
                               'distance_meters': 100, 'duration_seconds': 60}, headers=auth_headers(user))
        assert response.status_code == 422
        assert client.post('/api/v1/planned-routes', json={}).status_code == 401
