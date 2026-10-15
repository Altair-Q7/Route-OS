# RouteOS: a beginner-friendly software case study

> **Purpose:** This document explains the RouteOS application as a college-level
> developer might explain it to another student: what problem it solves, how the
> pieces fit together, how a route becomes a ride, where to read the code, and
> what could be improved next.

## 1. Executive summary

RouteOS is a delivery and driver-management product built on top of the
Organic Maps codebase. It is not a new map engine. Instead, it reuses Organic
Maps for the difficult geographic work and adds a product layer around it.

Organic Maps supplies:

- offline map files;
- map rendering;
- GPS/location handling;
- place search;
- road routing and turn-by-turn navigation;
- voice guidance and rerouting;
- track recording; and
- route geometry and map interaction.

RouteOS supplies:

- a driver-oriented user interface;
- shared saved routes;
- driver accounts and sessions;
- vehicle information for a ride;
- live location reporting to an administrator;
- delivery trips, supermarkets, standing orders and delivery outcomes;
- an optional ERPNext integration; and
- a read-only API for another business system to read confirmed deliveries.

The most important design decision is therefore **reuse instead of duplication**:

```text
RouteOS product features
        |
        | asks Organic Maps to calculate, draw, record or navigate
        v
Organic Maps geographic engine
        |
        +--> Android native host and Flutter product UI
        +--> Python/FastAPI backend for shared operational data
```

The current implementation is primarily Android-focused. Organic Maps still
contains Qt desktop and iOS applications, but the RouteOS product layer
described in this repository is integrated mainly into Android.

## 2. The problem the application solves

Imagine a small food producer delivering dosa and idli batter to supermarkets.
The business needs more than a map:

1. A driver needs to record or draw a useful route.
2. That route should be reusable by another driver.
3. The driver should choose a vehicle and start a ride.
4. A supervisor should see active drivers and their latest locations.
5. A delivery trip should say what was planned and what was actually delivered.
6. Shortages, failures and extra requests should be recorded rather than lost.
7. Another system should be able to read final delivery results safely.

Organic Maps already solves steps such as drawing a map, finding roads and
following a route. RouteOS adds the business workflow around those capabilities.

That separation is a useful product-engineering lesson: do not rebuild a mature
subsystem merely because the new product has a different user interface.

## 3. What is in the repository?

The repository has two identities:

1. It is a large Organic Maps source tree, mostly C++ with platform-specific
   Android, iOS and Qt code.
2. It contains a RouteOS product layer, currently concentrated in Flutter,
   Android integration code and a Python backend.

The most useful top-level areas are:

| Directory | Beginner-friendly description |
| --- | --- |
| `libs/` | Shared C++ map, search, routing, storage and rendering engine |
| `android/` | Android application, Java/Kotlin code, JNI wrappers and native SDK |
| `flutter_routeos/` | RouteOS product UI and route-planner state in Dart |
| `backend/` | FastAPI server, SQLite database setup, delivery logic and tests |
| `iphone/` | Organic Maps iOS application and Objective-C++/Swift bridges |
| `qt/` | Organic Maps desktop application built with Qt |
| `data/` | Map styles, symbols, translations and generated map-display assets |
| `3party/` | Third-party libraries built or consumed by the project |
| `tools/` | Build, generation, device and developer tools |
| `docs/` | Project documentation and this case study |

Start with these repository-written guides:

- `README-ROUTEOS.md` — current RouteOS workflow, build notes and verification
  status.
- `ROUTEOS_ARCHITECTURE.md` — RouteOS component diagram and integration points.
- `ROUTEOS_STRUCTURE.md` — short directory ownership summary.
- `flutter_routeos/README.md` — Flutter/native boundaries and route-planner
  constraints.
- `backend/README.md` — server setup, authentication and deployment notes.
- `backend/DELIVERY.md` — supermarket and delivery rules.
- `backend/CLIENT_API.md` — read-only external reporting API.
- `docs/STRUCTURE.md` — broader Organic Maps source-tree explanation.

## 4. The architecture in plain English

### 4.1 Three major layers

RouteOS can be understood as three cooperating layers:

```text
Layer 1: Flutter product UI
  Buttons, screens, route lists, planner, delivery screens

Layer 2: Android host and bridge
  Owns the real map surface, talks to Organic Maps and calls the backend

Layer 3: Shared Organic Maps engine + RouteOS backend
  C++ geographic engine on the device; Python business API on the server
```

The device side and the server side have different jobs:

| Location | Main job |
| --- | --- |
| Device | Respond quickly, render maps, use GPS, calculate routes and navigate |
| Backend | Share routes, identify users, store rides, receive GPS and store delivery facts |

The backend does **not** calculate the road route. The phone sends waypoints to
the native Organic Maps engine, gets back a route, and saves the resulting
business metadata to the server.

### 4.2 A useful analogy

Think of the app as a restaurant:

- Organic Maps is the kitchen equipment: reliable, specialised and complicated.
- Flutter is the dining room: it presents the product experience to the user.
- Android Java is the waiter and building manager: it connects the user-facing
  room to the kitchen and handles Android lifecycle rules.
- The backend is the order book and office: it remembers shared data and lets
  supervisors coordinate drivers.

The dining room should not try to cook the route itself. The office should not
try to draw the map. Each layer has a clear responsibility.

## 5. Startup: how the application comes to life

### 5.1 Android startup

The broad Android sequence is:

```text
MwmApplication
    |
    v
SplashActivity
    |
    v
OrganicMaps / native Framework initialization
    |
    v
MwmActivity
    |
    +--> Organic Maps native map and services
    +--> RouteOS Flutter shell and overlays
```

Important files to read:

- `android/app/src/main/java/app/organicmaps/MwmApplication.java`
- `android/app/src/main/java/app/organicmaps/SplashActivity.java`
- `android/app/src/main/java/app/organicmaps/MwmActivity.java`
- `android/sdk/src/main/java/app/organicmaps/sdk/OrganicMaps.java`
- `android/sdk/src/main/java/app/organicmaps/sdk/Framework.java`
- `android/sdk/src/main/cpp/app/organicmaps/sdk/Framework.cpp`

`MwmActivity` is especially important. It is the integration hub that hosts the
native map and the RouteOS UI. It also coordinates RouteOS ride state with
Organic Maps navigation and background services.

### 5.2 Shared-engine startup

The Organic Maps C++ `Framework` is the application-level coordinator for the
geographic engine. It connects map data, search, routing, storage, bookmarks,
rendering and location-related state.

Read:

- `libs/map/framework.hpp`
- `libs/map/framework.cpp`

The framework is not itself every subsystem. It is more like a conductor:

```text
Framework
  +--> DataSource / FeaturesFetcher: read local .mwm map files
  +--> SearchAPI: search and reverse geocoding
  +--> RoutingManager: build and follow routes
  +--> Storage: download and remove map regions
  +--> DrapeEngine: render the map scene
  +--> BookmarkManager: bookmarks and tracks
  +--> Traffic / transit / isolines managers
```

Map loading is important because offline routing cannot work without the right
regional map files. Storage knows which regions exist and which are downloaded;
the data source registers those local files so search and routing can use them.

## 6. The Flutter product UI

The Flutter module is a product shell, not a standalone map application.
`flutter_routeos/README.md` explicitly says that the host owns the real native
map view.

Important Dart files:

- `flutter_routeos/lib/main.dart` — Flutter entry point.
- `flutter_routeos/lib/app/app.dart` — application shell and theme.
- `flutter_routeos/lib/home/home.dart` — home screen, routes and ride actions.
- `flutter_routeos/lib/map/native_map.dart` — embedded native map view.
- `flutter_routeos/lib/routing/planner.dart` — waypoint and planner state.
- `flutter_routeos/lib/core/bridge.dart` — Dart-to-native method/event channels.
- `flutter_routeos/lib/deliveries/` — delivery and admin product screens.

The planner is a good first file for a beginner because it is mostly ordinary
application state:

- `RoutePoint` stores latitude, longitude, label and address.
- `PlannerState` describes whether the planner is idle, drawing, calculating,
  ready, saving, navigating or in an error state.
- `_points` stores the ordered route points.
- `_undo` and `_redo` store editing history.
- `add`, `remove`, `move`, `insert`, `reorder`, `undo` and `redo` modify points.
- `json()` and `restore()` support draft persistence.

The planner deliberately does not calculate roads in Dart. It sends the points
through a platform channel and asks the native Organic Maps engine to calculate
the road route.

### 6.1 Dart/native communication

`flutter_routeos/lib/core/bridge.dart` defines two channels:

```dart
MethodChannel('routeos/v1/methods')
EventChannel('routeos/v1/events')
```

The method channel is for requests such as “calculate this route” or “start the
ride”. The event channel is for messages coming back, such as route-ready,
navigation-progress, map-tap or recording-progress events.

The envelope includes a protocol version and data object:

```text
{ version: 1, data: {...} }
```

This is a small but valuable design choice. It makes it possible to reject or
upgrade incompatible bridge messages instead of silently misreading them.

## 7. The most important user flow: route to ride

### 7.1 Recording a route

The recorded-route flow is:

```text
Driver starts recording
  -> Organic Maps receives GPS points
  -> TrackRecordingService continues recording
  -> RouteOS receives progress/track data
  -> Driver previews and names the route
  -> RouteOS uploads the track and route metadata to the backend
```

The original track is kept. For long recordings, the navigation engine may use
simplified anchor points because Organic Maps supports at most 102 total route
points. The saved recording and the later navigation approximation are therefore
not always identical.

Read:

- `android/app/src/main/java/app/organicmaps/location/TrackRecordingService.java`
- `android/app/src/main/java/app/routeos/RouteOsRecordingSession.java`
- `flutter_routeos/lib/home/home.dart`
- backend endpoints in `backend/app.py` for `/tracks` and `/routes`.

### 7.2 Drawing a route

The drawn-route flow is:

```text
Driver taps map
  -> Flutter creates ordered start/via/destination points
  -> Flutter calls the native bridge
  -> Organic Maps calculates roads offline
  -> Native result returns distance, duration and geometry
  -> Flutter previews the route
  -> Backend stores the waypoint definition and route statistics
```

Route point rules are simple enough to remember:

- first point is `start`;
- last point is `destination`;
- points between them are `via` points; and
- the engine limit is 102 total points.

The backend validates the same basic shape. This is important because client
validation alone can be bypassed by another HTTP client.

### 7.3 Starting a ride

Once a driver chooses a saved route:

1. RouteOS asks for vehicle type and vehicle number.
2. Native navigation first rebuilds the route from the actual current GPS
   position.
3. The app calls `POST /api/v1/rides`.
4. The server checks the authenticated driver, route and active-ride rule.
5. The server returns a ride identifier.
6. Android stores enough local state to restore the ride after recreation.
7. Organic Maps starts turn-by-turn navigation.

The ride state can be viewed as:

```text
idle -> vehicle selection -> active ride -> arrived/ending -> ended
```

The backend enforces one active ride per driver with a partial unique index. That
is a strong example of putting an important business rule in the database as
well as in the user interface.

### 7.4 Live location reporting

During an active ride, the Android navigation service periodically sends the
latest GPS sample to:

```text
POST /api/v1/rides/{ride_id}/locations
```

The current design aims for approximately one sample every five seconds. The
backend stores latitude, longitude, time, speed and bearing when available.

The server then exposes active rides for the administrator. A stale flag is
useful: a marker on a map should not look “live” if the last sample is old.

An important conceptual distinction:

> GPS can show that the vehicle was near a place. It does not prove that goods
> were handed over.

That is why delivery confirmation is a separate workflow.

## 8. Delivery workflow

The delivery extension is documented in `backend/DELIVERY.md` and implemented
through `backend/erpnext_integration.py` plus the delivery code in `app.py`.

The business model is:

```text
Supermarket directory
  -> standing order
  -> delivery trip
  -> ordered stops
  -> driver ride
  -> per-stop confirmation
  -> report / client API
```

The important entities are:

| Entity | Meaning |
| --- | --- |
| Supermarket | A shop with address, coordinates and active/inactive state |
| Standing order | The shop's usual planned quantities |
| Delivery trip | A particular run with a driver, vehicle and ordered stops |
| Stop | One supermarket visit in that trip |
| Delivery event | Immutable record of a confirmed outcome |
| Extra request | Additional quantity requested for a later allocation |

Quantity rules make the workflow predictable:

- delivered quantity cannot exceed planned quantity;
- a complete delivery must match the planned quantity;
- a partial delivery must explain the shortage;
- a failed delivery must explain why; and
- a final outcome cannot be overwritten casually.

This is a good example of domain rules being encoded in validation instead of
being left as instructions in a README.

## 9. Backend architecture

### 9.1 Technology choice

The backend is a small Python application using FastAPI and SQLite:

- FastAPI turns Python functions into HTTP endpoints.
- Pydantic models validate incoming JSON.
- `sqlite3` stores users, routes, rides, locations and delivery data.
- Uvicorn runs the web server.

The main entry point is `backend/app.py`. It contains database setup, request
models, authentication dependencies, route/ride endpoints and application
lifecycle code. Delivery-specific setup and operations are also connected from
`backend/erpnext_integration.py`.

### 9.2 Database startup

On startup, `initialize_database()`:

1. opens SQLite with foreign keys enabled;
2. enables WAL mode and a busy timeout;
3. creates missing tables;
4. adds columns needed by older local databases;
5. creates indexes and the one-active-ride constraint; and
6. initializes delivery tables.

This is convenient for an MVP because a developer can start the service without
running a separate migration command. The trade-off is that schema history is
implicit and the startup migration code becomes more difficult to manage as the
system grows.

Core tables include:

```text
users -> sessions
users -> recorded_tracks -> routes -> rides -> live_locations
users <-> route_favorites / route_recents
events and client_keys support auditing and external access
```

Delivery records add supermarkets, standing orders, assignments, events and
extra requests. Some trip details are stored as JSON snapshots so the history
of a trip is preserved even if a supermarket is later renamed.

### 9.3 Authentication

There are two intentionally different authentication patterns:

1. Driver/admin sessions use `Authorization: Bearer <token>`.
2. External reporting clients use `X-RouteOS-Client-Key: <key>`.

Production passwords are hashed with PBKDF2-HMAC-SHA256. The server returns a
random session token, but stores only its SHA-256 hash. Sessions expire after 24
hours and logout removes the session.

Development quick login is guarded by `ROUTEOS_DEVELOPMENT_AUTH=1`. It is useful
for a local demo, but it must not be enabled on a public deployment.

The server does not trust a client-supplied driver ID by itself. It compares the
requested identity with the identity represented by the bearer session and
checks the user's role. This is the security rule a beginner should look for
when reading every protected endpoint:

```text
Who is calling?
What role do they have?
Which record are they allowed to access?
```

## 10. Optional ERPNext integration

ERPNext is treated as an optional system of record for ERP delivery information.
RouteOS reads eligible delivery trips and delivery-note information, then writes
only a custom `RouteOS Delivery Tracking` document.

The integration intentionally does not modify ERPNext stock, invoices, payments,
delivery notes or standard trip status. This boundary reduces the chance that a
GPS/delivery application accidentally changes accounting or inventory data.

The sync process uses deterministic names and retries with backoff. That makes a
retry safe: the same RouteOS assignment updates the same ERPNext tracking
document instead of creating endless duplicates.

Read:

- `backend/ERPNEXT.md`
- `backend/erpnext_integration.py`
- `backend/setup_erpnext.py`
- `backend/tests/test_erpnext.py`

## 11. How rendering works

The map is rendered by the Organic Maps Drape engine rather than by Flutter.
The high-level path is:

```text
Map data + style rules
  -> FeaturesFetcher / DataSource
  -> Drape frontend scene
  -> graphics backend (OpenGL/Vulkan/Metal depending on platform)
  -> native map surface
  -> Flutter/Android UI is composited around it
```

Important directories:

- `libs/drape/` — lower-level graphics abstractions.
- `libs/drape_frontend/` — map scene, labels, routes and overlays.
- `libs/shaders/` — shader-related assets and tests.
- `libs/indexer/` — map features, classifiers and drawing rules.
- `data/styles/` — source map styles.
- `data/symbols/` — symbols and visual assets.

This is why a RouteOS developer should not start by searching for a Dart map
widget that draws roads. The real road renderer is in the native engine.

## 12. Cross-language boundaries

RouteOS crosses several languages. Each boundary has a different purpose:

| From | To | Mechanism | Why it exists |
| --- | --- | --- | --- |
| Flutter/Dart | Android Java | Flutter `MethodChannel` / `EventChannel` | Product UI requests native work |
| Java | C++ | JNI | Android calls the shared map/routing engine |
| Java | Backend | HTTP client in `android/sdk/src/main/java/app/routeos/RouteOsApi.java` | Shared business state and telemetry |
| C++ | Android | platform abstractions and JNI callbacks | GPS, rendering and native results |
| Swift/Objective-C | C++ | iOS CoreApi / Objective-C++ | Organic Maps iOS bridge |
| Qt | C++ | direct C++ calls and Qt widgets | Desktop Organic Maps application |

When debugging, first identify which boundary failed:

- Did the Flutter button fire?
- Did the method-channel message reach Java?
- Did Java call the correct JNI method?
- Did C++ calculate a route?
- Did the HTTP request reach FastAPI?
- Did SQLite accept the transaction?

This approach is much faster than treating the entire application as one large
program.

## 13. Build and run map for a student

### Backend first

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
ROUTEOS_DEVELOPMENT_AUTH=1 \
  .venv/bin/uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Then check:

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/api/v1/manifest
```

Backend checks:

```bash
.venv/bin/python -m py_compile app.py
.venv/bin/pytest -q
```

### Flutter checks

From `flutter_routeos/`:

```bash
flutter analyze
flutter test
```

Flutter is normally built as an AAR because the Organic Maps Android build uses
its own Gradle setup:

```bash
flutter build aar --no-debug --no-profile --release \
  --build-number=1 --output="$PWD/build"
```

### Android build

```bash
cd android
./gradlew -Parm64 :app:assembleGoogleDebug
```

For a local backend on a connected device or emulator:

```bash
adb reverse tcp:8000 tcp:8000
```

The exact Organic Maps environment setup is in `docs/INSTALL.md`. A complete
Android build requires the Android SDK/NDK, CMake, Java and the expected map
assets. Do not replace a missing real map asset with an empty file: offline
routing needs valid map data.

## 14. A practical code-reading route

Do not try to read the entire repository from top to bottom. Use one vertical
slice at a time.

### Slice A: understand startup

1. `android/app/src/main/java/app/organicmaps/MwmApplication.java`
2. `android/app/src/main/java/app/organicmaps/SplashActivity.java`
3. `android/app/src/main/java/app/organicmaps/MwmActivity.java`
4. `flutter_routeos/lib/main.dart`
5. `flutter_routeos/lib/app/app.dart`

### Slice B: understand route planning

1. `flutter_routeos/lib/routing/planner.dart`
2. `flutter_routeos/lib/core/bridge.dart`
3. `android/app/src/main/java/app/routeos/bridge/`
4. native Framework routing methods under `android/sdk/src/main/cpp/`
5. `libs/map/routing_manager.cpp`
6. `libs/routing/`

### Slice C: understand a ride

1. `flutter_routeos/lib/home/home.dart`
2. `android/app/src/main/java/app/routeos/RouteOsNavigationOverlay.java`
3. `android/libs/routing/src/main/java/app/organicmaps/routing/NavigationService.java`
4. `backend/app.py` ride endpoints
5. `backend/tests/test_rides.py`
6. `backend/tests/test_arrival.py`

### Slice D: understand delivery operations

1. `flutter_routeos/lib/deliveries/`
2. `backend/DELIVERY.md`
3. `backend/erpnext_integration.py`
4. `backend/tests/test_native_trips.py`
5. `backend/tests/test_reports.py`
6. `backend/CLIENT_API.md`

For each slice, write down the request and response data. This turns “many
files” into a sequence of messages.

## 15. Testing strategy

The repository has tests at multiple levels:

### Backend tests

`backend/tests/` covers authentication, sessions, permissions, routes, rides,
arrival rules, delivery trips, reports, ERPNext, client keys and regressions.

These tests are valuable because business rules are easier to test at the HTTP
boundary than only through UI clicks.

### Flutter tests

`flutter_routeos/test/` covers planner and product UI behavior. The planner is a
good candidate for unit tests because its state transitions are deterministic.

### Native and device checks

Some failures only appear on a real device: map surfaces, JNI symbols, Android
activity recreation, background GPS, navigation and platform composition.
`README-ROUTEOS.md` records device verification and also clearly lists items that
were not yet verified. That distinction is good engineering practice.

### What a test should prove

For a new feature, ask three questions:

1. Does the pure logic work?
2. Does the HTTP or bridge contract work?
3. Does the real Android/device lifecycle work?

For example, a new “pause ride” feature needs planner/ride logic tests, backend
authorization/state tests, and an Android background/foreground test.

## 16. Strengths of the design

### Reusing a mature geographic engine

The project gets offline maps, routing, search and rendering without implementing
those from scratch.

### Clear business boundary

The backend stores shared operational facts; the device remains responsible for
fast local geographic behavior.

### Server-side authorization

The backend checks bearer identity and roles rather than trusting the driver ID
sent by the phone.

### Good idempotency ideas

GPS samples can include a client-generated sample ID and retries can be
deduplicated. ERPNext sync uses deterministic document identities. These ideas
matter whenever networks are unreliable.

### Useful historical behavior

Routes are soft-deleted rather than immediately destroying ride history. Delivery
outcomes are treated as final. JSON snapshots preserve what a trip looked like at
the time it was created.

### Explicit MVP limitations

The existing documentation calls out limits such as 102 routing points, lack of
alternative-route selection through current Android JNI, Android-focused RouteOS
integration, and unverified production signing/deployment. Honest limitations
help future developers avoid depending on behavior that is not guaranteed.

## 17. Main risks and improvement opportunities

These are improvement directions, not claims that the application is unusable.

### 17.1 Move production persistence beyond one SQLite file

SQLite is excellent for local development and a small single-process MVP. It is
less comfortable for a growing delivery operation because all shared data lives
in one file and the service is designed around one worker.

Possible progression:

1. Keep SQLite for local development and tests.
2. Introduce explicit schema versions and migration tests.
3. Add backups and restore drills.
4. Move hosted production to PostgreSQL when concurrent users and data volume
   justify it.

### 17.2 Add a GPS retention policy

Uploading every five seconds creates a lot of rows over time. Decide:

- how long raw locations are retained;
- whether old points are downsampled;
- whether only the latest point is needed for the admin map;
- what delivery evidence must be kept; and
- how database size is monitored.

### 17.3 Strengthen account administration

Account creation and password lifecycle should match the actual business. A
production system normally needs admin-controlled invitations, disablement,
password reset and audit history rather than only demo provisioning.

### 17.4 Add rate limiting and observability

Login throttling is present, but a production service should also monitor:

- request rates per account/client key;
- large track uploads;
- GPS upload frequency;
- stale active rides;
- database size and write failures;
- ERPNext sync retries; and
- latency and error rates.

Use request IDs and structured logs, while never logging passwords or bearer
tokens.

### 17.5 Split the largest integration hub

`MwmActivity.java` is a powerful integration point, but a very large activity is
hard to reason about and test. A future refactor could extract:

- a RouteOS ride coordinator;
- a RouteOS navigation adapter;
- a Flutter host controller;
- a backend session/repository object; and
- lifecycle-aware state holders.

Do this incrementally. The risk is not “large file = bug”; the risk is that UI,
navigation, backend and lifecycle responsibilities become too tightly coupled.

### 17.6 Keep documentation consistent

Some short structure documents describe the earlier minimal backend, while the
current tree also contains delivery, ERPNext and client-key functionality. A
future improvement would be to publish one generated endpoint index and clearly
separate:

- core RouteOS API;
- native delivery API;
- ERPNext integration; and
- external read-only client API.

## 18. Example improvement roadmap for a student team

### Beginner project

- Add a backend endpoint test for a missing/invalid route.
- Add a Flutter planner test for undo after reorder.
- Improve an error message while preserving the bridge envelope.
- Add a README diagram for one flow.

### Intermediate project

- Add cursor pagination to routes or delivery reports.
- Add GPS retention/downsampling as a tested background task.
- Extract backend auth dependencies into a dedicated module.
- Add structured telemetry for stale rides.

### Advanced project

- Introduce versioned database migrations.
- Add PostgreSQL support behind a repository interface.
- Build a web admin dashboard using the existing read/write API.
- Add signed delivery evidence or recipient confirmation.
- Add a dedicated sync worker for ERPNext.
- Replicate the RouteOS product layer on iOS using Swift/Objective-C++.

For every project, keep the change narrow, add tests at the relevant boundary,
and avoid changing Organic Maps core behavior unless the product genuinely needs
it.

## 19. Glossary

| Term | Meaning |
| --- | --- |
| API | A set of HTTP or programming operations another component can call |
| Backend | The server that stores shared data and applies business rules |
| Bearer token | A secret string: whoever presents it is treated as the session owner |
| Drape | Organic Maps' native rendering system |
| JNI | The bridge that lets Java call C++ on Android |
| MWM | Organic Maps' generated offline map-file format |
| Native | Code running in the platform/C++ layer rather than Flutter |
| Route | A saved planned or recorded path that drivers can reuse |
| Ride | One driver's active execution of a route with a vehicle |
| Stop | One supermarket visit within a delivery trip |
| Waypoint | A user-selected route point: start, via or destination |
| Soft delete | Marking something deleted while retaining it for history |

## 20. Final mental model

If you remember only one picture, remember this:

```text
                 RouteOS product layer
       Flutter UI + Android integration + FastAPI
                    /              \
                   /                \
          asks local engine       stores shared facts
                 /                    \
                v                      v
       Organic Maps C++ engine       SQLite/ERPNext
       maps, GPS, routing,           users, routes, rides,
       rendering, navigation         deliveries, reports
```

The best way to improve RouteOS is to preserve that separation. Add business
features around the map engine, use the native engine for geographic truth, put
authorization and invariants on the server, and test every cross-language
boundary deliberately.

## Sources in this repository

This case study was prepared by reading the current repository code and the
following project documentation:

- `README-ROUTEOS.md`
- `ROUTEOS_ARCHITECTURE.md`
- `ROUTEOS_STRUCTURE.md`
- `flutter_routeos/README.md`
- `backend/README.md`
- `backend/DELIVERY.md`
- `backend/CLIENT_API.md`
- `docs/STRUCTURE.md`
- representative files under `flutter_routeos/`, `android/`, `libs/` and
  `backend/`.

The working tree already contained unrelated modifications in five Flutter
files while this document was prepared. They were left untouched.
