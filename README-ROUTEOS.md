# RouteOS

RouteOS now replaces the visible Organic Maps interface while retaining the
Organic Maps map renderer, offline data, GPS recording, routing, and track
import engine underneath.

The implemented MVP workflow is:

```text
Quick login → RouteOS record/draw → Organic Maps track geometry → named shared
route → another driver selects it → vehicle choice → active ride → Organic Maps
navigation → admin live tracking → end ride
```

- Quick-login accounts are Disha Patani and Sukumara Kurup (drivers), and
  Thomachan Valiparambil (admin).
- Search combines saved RouteOS routes with Organic Maps' native offline place
  search.
- The current GPS position is the hub for every new route.
- **Draw Route** supports multiple crosshair waypoints and previews a real
  Organic Maps road route before saving its sampled geometry.
- **Record Route** captures GPS from the foreground recording service, including
  while the map activity is not in the foreground.
- Saved routes are shared globally, so every signed-in driver sees them.
- Vehicle type and number are stored only on a ride; there is no fleet module.
- During a ride the driver uploads the latest GPS location every five seconds.
  The admin map polls active rides and stops showing a driver after End Ride.
- The backend stores users, tracks, routes, rides, and live locations only.

## Build the app

Follow Organic Maps' Android setup in `docs/INSTALL.md`, then build from
`android/` using the existing Organic Maps Gradle workflow.

## Run the backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app:app --reload --port 8000
```

For a USB-connected device or an emulator, expose the development backend with:

```bash
adb reverse tcp:8000 tcp:8000
```
