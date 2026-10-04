# RouteOS backend foundation

This is the minimal product-data boundary for the Organic Maps based RouteOS
MVP. Organic Maps remains responsible for geographic behavior.

## Run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
ROUTEOS_DEVELOPMENT_AUTH=1 .venv/bin/uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

The API is available at `http://127.0.0.1:8000`.

## MVP workflow API

The MVP API provides:

- `GET /health` — liveness probe; the Android client checks it before login.
- `POST /api/v1/users` — create an account (startup seeding uses the same path).
- `POST /api/v1/auth/login` — password login, or seeded quick-login in explicitly enabled development mode.
- `POST /api/v1/auth/logout` — revoke the current bearer session.
- `POST /api/v1/planned-routes` — persist ordered waypoints and native OM distance/duration.
- `POST /api/v1/tracks` — save the recorded Organic Maps track reference and
  portable GPS points.
- `POST /api/v1/routes` — name and publish a track as a shared RouteOS route.
- `GET /api/v1/routes` — list routes available to another driver.
- `GET /api/v1/routes/{id}` — retrieve the route and its track points for native
  Organic Maps import/navigation.
- `POST /api/v1/rides` — start a route with a simple vehicle type and number.
- `POST /api/v1/rides/{id}/locations` — publish the driver's current location.
- `GET /api/v1/rides/active` — list active rides for the admin map.
- `POST /api/v1/rides/{id}/end` — end the ride and stop live tracking.
- `GET /api/v1/drivers/{id}/active-ride` — resume an interrupted ride on login.
- `POST /api/v1/events` — append a RouteOS activity event.
- `GET /api/v1/events` — recent RouteOS activity log.
- `GET /api/v1/manifest` — product metadata and the supported feature list.

The seeded users are D.B Cooper and Sukumara Kurup as drivers, and Sreekandan
Nair as admin.

## Authentication and deployment

Passwordless quick login is disabled by default. `ROUTEOS_DEVELOPMENT_AUTH=1` is
only for a local development backend, never a public server. Production login
requires a password and returns a random bearer token; only its SHA-256 hash is
stored in the sessions table. Sessions expire after 24 hours and logout revokes
them. Client-supplied driver IDs do not grant permission: bearer identity and
roles are checked on the server.

Provision passwords for existing seeded accounts before production startup:

```bash
.venv/bin/python provision_password.py 'D.B Cooper'
.venv/bin/python provision_password.py 'Sukumara Kurup'
.venv/bin/python provision_password.py 'Sreekandan Nair'
ROUTEOS_DEVELOPMENT_AUTH=0 .venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
```

The tool prompts securely and revokes earlier sessions. Put production behind
HTTPS. Release Android builds require a configured HTTPS URL; debug builds allow
ADB loopback only. Android uses Keystore AES-GCM rather than plaintext tokens.
Set `ROUTEOS_DATABASE` to the persistent SQLite path and `ROUTEOS_CORS_ORIGINS`
to explicit allowed origins if browser clients are used. Back up the database
before deploying; startup migrations preserve existing routes/tracks/rides.

The Android client targets `http://127.0.0.1:8000`, so expose the backend to the
device or emulator with `adb reverse tcp:8000 tcp:8000` (see `README-ROUTEOS.md`).

## Verify

```bash
.venv/bin/python -m py_compile app.py                  # syntax check
.venv/bin/pytest -q
.venv/bin/uvicorn app:app --port 8000                  # then: curl /health
curl -s http://127.0.0.1:8000/api/v1/manifest | python3 -m json.tool
```
