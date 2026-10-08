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

- `GET /health` — checks that the backend can open its database.
- `POST /api/v1/users` — create a driver account.
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
- `POST /api/v1/rides/{id}/arrive` — confirm arrival within 150 metres of the destination using GPS no older than two minutes.
- `GET /api/v1/drivers/{id}/active-ride` — resume an interrupted ride on login.
- `POST /api/v1/events` — admin-only custom activity events; server action kinds are reserved.
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

For a Render Web Service, use `backend` as the Root Directory, `pip install -r
requirements.txt` as the Build Command, and the following Start Command:

```bash
python -u serve.py
```

Set the Health Check Path to `/health`. Render must receive the service port from
`$PORT`; binding only to `127.0.0.1` or hard-coding port `8000` causes deployment
port detection to time out. The repository root also contains `render.yaml` with
these settings for Blueprint-based deployment.

The launcher reads Render's `PORT`, binds to `0.0.0.0`, and uses one worker with
Python's asyncio loop and the h11 HTTP implementation. It logs each startup stage
immediately; database readiness still completes before the service accepts requests.
For an existing dashboard-created service, update its Start Command manually:
changing `render.yaml` alone does not change that service's settings.

The tool prompts securely and revokes earlier sessions. Put production behind
HTTPS. Release Android builds require a configured HTTPS URL; debug builds allow
ADB loopback only. Android uses Keystore AES-GCM rather than plaintext tokens.
Set `ROUTEOS_DATABASE` to the persistent SQLite path and `ROUTEOS_CORS_ORIGINS`
to explicit allowed origins if browser clients are used. Back up the database
before deploying; startup migrations preserve existing routes/tracks/rides.

The Android client defaults to `https://route-os-backend.onrender.com`. To use a
local backend, configure `http://127.0.0.1:8000` in a debug build and expose it with
`adb reverse tcp:8000 tcp:8000`. Changing servers signs out the current account;
end any active ride or recording first.

Startup preserves provisioned passwords and existing sessions. Seeded accounts
have no production password until explicitly provisioned.

On Render plans without Shell access, set the secret environment variable
`ROUTEOS_DEMO_PASSWORD` to a demo password of 7–256 characters (`Demo123` is supported).
Regular account passwords still require at least 12 characters. When the demo password changes, the
backend provisions it for all three seeded demo accounts and revokes
their previous sessions. Keep `ROUTEOS_DEVELOPMENT_AUTH=0`; this preserves normal
password authentication without exposing passwordless login.

## Render reliability and saved data

Render Free sleeps after 15 minutes without requests and can take about a minute
to wake up. RouteOS allows up to 75 seconds for login and reads; a slow response
keeps the map and app screen open. A missing or expired login offers Sign in.
Restarting a server with the same demo password now preserves existing sessions.

The default SQLite file is **not durable on Render Free**. Restarting, redeploying,
or sleeping can erase newly saved routes, rides, and login sessions. Client fixes
cannot prevent that data loss. See https://render.com/docs/free.

For a reliable deployment with the current backend:

1. Select an always-on Render web service and attach a persistent disk at
   `/var/data` (this is a paid hosting change).
2. Set `ROUTEOS_DATABASE=/var/data/routeos.db` and keep one Uvicorn worker.
3. Back up and copy any existing database to that disk before switching paths.
   Export routes before redeploying a Free service; do not assume its data survives.
4. Keep `ROUTEOS_DEMO_PASSWORD` unchanged unless deliberately resetting passwords.

If you need to keep free web hosting, a separate durable database and a backend
migration are required. This backend currently uses SQLite, not PostgreSQL.

Android navigation persists up to 1,000 GPS samples in an account/server-scoped
SQLite outbox and retries network/server failures with backoff. Samples include
`sample_id`, UTC `recorded_at`, and optional `accuracy_meters`; retries are
deduplicated by `(ride_id, sample_id)`. Admin markers use the newest recorded
timestamp and flag GPS older than 30 seconds. Expired sessions retain queued
samples and allow the same driver to sign in during a ride. Native arrival keeps
tracking active until an explicit server-confirmed End Ride.

## Verify

```bash
.venv/bin/python -m py_compile app.py                  # syntax check
.venv/bin/pytest -q
.venv/bin/uvicorn app:app --port 8000                  # then: curl /health
curl -s http://127.0.0.1:8000/api/v1/manifest | python3 -m json.tool
```
