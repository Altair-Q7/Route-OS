# RouteOS

RouteOS now replaces the visible Organic Maps interface while retaining the
Organic Maps map renderer, offline data, GPS recording, routing, and track
import engine underneath.

The implemented MVP workflow is:

```text
Quick login → RouteOS record/draw → Organic Maps track geometry → named shared
route → another driver selects it → vehicle choice → active ride → Organic Maps
navigation → delivery quantities and outcomes → admin live tracking → end ride
```

- Quick-login accounts are D.B Cooper and Sukumara Kurup (drivers), and
  Sreekandan Nair (admin).
- Search combines saved RouteOS routes with Organic Maps' native offline place
  search.
- Native GPS can supply a route point or recenter the map. Navigation rebuilds
  from the actual current position before creating the backend ride.
- **Draw Route** uses Flutter controls over the native map. Tap to add ordered
  start/via/destination points; move, insert, delete, reorder, clear, undo and redo
  recalculate through Organic Maps. Planned routes save their waypoint definition
  and native distance/time; they are not fabricated GPS recordings.
- **Record Route** captures GPS from the foreground recording service, including
  while the map activity is not in the foreground.
- Saved routes are shared globally, so every signed-in driver sees them.
- Route owners and admins can permanently remove routes after confirmation. A
  route used by a completed ride can still be removed; its completed ride audit
  history is retained as a hidden backend tombstone. A route cannot be removed
  while an active ride is using it.
- Vehicle type and number are stored only on a ride; there is no fleet module.
- During a ride the driver captures live GPS every five seconds. Offline samples
  are durable and uploaded in batches when connectivity returns.
- The admin map updates stable driver markers in place, so a refresh no longer
  clears the marker layer or forces the viewport away from what the admin is
  inspecting.
- Admins can create delivery trips directly in RouteOS, assign product quantities
  per supermarket, link them to a driver's ride, and review shortages, failures,
  extra requests, and delivered totals. ERPNext synchronization is optional;
  RouteOS delivery tracking also works on its own.
- The backend stores RouteOS users, routes, rides, telemetry, delivery operations,
  and audit history. It does not duplicate Organic Maps routing or map data.

## Build the app

Follow Organic Maps' Android setup in `docs/INSTALL.md` (SDK, NDK, CMake and Java),
install Flutter, and initialise the repository's pinned submodules:

```bash
git submodule update --init --recursive
bash tools/build-routeos-flutter-aar.sh
cd android
./gradlew -Parm64 :app:assembleGoogleDebug
./gradlew -Parm64 :app:lintGoogleDebug
```

For a tester release build:

```bash
bash tools/build-routeos-flutter-aar.sh
cd android
./gradlew -Parm64 :app:assembleGoogleRelease -ProuteOsDemoRelease=true
```

`routeOsDemoRelease` uses the repository's demo certificate and is suitable only
for sideloaded testing. A Play Store or managed-device release must instead use a
private production key configured in `android/app/secure.properties`; never
commit that file or its passwords.

Do not commit generated Flutter AARs or `.android`. Rebuild the AAR after Dart
changes. Google builds require the real `data/World.mwm` asset, supplied according
to the Organic Maps setup; deleting it or making an empty substitute is not a fix.
This workspace's missing asset was restored from its existing Organic Maps tree.
An independent clean-checkout build has not yet been verified.

Flutter is hosted inside `MwmActivity`, which retains native map/service ownership.
`flutter_routeos/` contains product UI and planner state; `app/routeos/bridge/`
contains the Android adapter; the API/Keystore client is under `android/sdk/`.
The existing Java product screens remain fallbacks, not the default launch UI.
The SDK's native-build skip now applies only to lint-only invocations. Combined
assembly/lint must rebuild JNI; otherwise new Java declarations can be packaged
with an older native library. This defect was discovered through a phone crash,
fixed, and the rebuilt library's RouteOS JNI exports were checked directly.

## Run the backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
ROUTEOS_DEVELOPMENT_AUTH=1 .venv/bin/uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

For a USB-connected device or an emulator, expose the development backend with:

```bash
adb reverse tcp:8000 tcp:8000
```

For production password provisioning and HTTPS see `backend/README.md`.
Development quick-login must not be exposed on a public backend.

## Device smoke checks

Install the Google debug APK and launch its existing resource-downloader entry:

```bash
adb install -r android/app/build/outputs/apk/google/debug/RouteOS-*-google-debug.apk
adb shell am start -n app.routeos.debug/app.organicmaps.DownloadResourcesActivity
python3 tools/routeos-device-ui.py --expect RouteOS
```

`tools/routeos-device-ui.py --tap LABEL` uses Android accessibility labels to
exercise the real installed UI. Wait for installation and each assertion to
finish; do not run concurrent ADB interaction scripts. Road routing requires the
relevant regional offline map. Actual turn-by-turn/rerouting and multi-turn
recording still require a physical driving test.

## Verification on 15 October 2026

The current Alpha 2.4 tree was checked with the backend and Flutter suites,
Android JVM tests, full Android lint, a phone-app release build, and focused
location-outbox instrumentation on the connected Nothing A142.

| Current automated check | Result |
| --- | --- |
| Backend tests | PASS — 183 tests |
| Backend process `/health` and manifest smoke test | PASS |
| Flutter analysis | PASS — no issues |
| Flutter tests | PASS — 53 tests |
| Android Google debug assembly and JVM tests | PASS |
| Android full-module lint | PASS — 0 errors; 1,381 inherited warnings; see tooling caveat below |
| Location store/uploader instrumentation on phone | PASS — 8 tests |
| Google phone-app release assembly | PASS |
| APK v2 signature verification | PASS — demo certificate, not production signing |
| Release reinstall / RouteOS launch / system Back to launcher | PASS on Nothing A142 |

The repository-wide Google release task also includes the optional Wear app,
which correctly refuses to produce a release without its own private keystore.
The RouteOS phone release target above is the supported tester build command.

### Earlier manual device coverage

The installed Android debug build runs actual Flutter product UI with the native
Organic Maps platform view on the connected Nothing A142. Regional Kerala and
Tamil Nadu maps are installed; these checks do not substitute screenshots or a
network routing service for the map engine.

The following manual checks were completed on 2 October 2026. They were not all
repeated by the final automated pass, so they are recorded separately rather
than presented as fresh release evidence.

| Manual check | Result |
| --- | --- |
| Clean Android debug assembly | PASS |
| Native JNI instrumentation on phone | 2 passed, including 2,000-point anchor input |
| Installation / Flutter launch / native map / real map taps | PASS |
| Two-point and four-point native road routing | PASS |
| Editing, insertion, deletion, reordering, undo/redo | PASS; reordering verified through Move earlier/later actions |
| Save / reload / another driver sees saved route | PASS |
| Native GPS navigation start / explicit ride end / live GPS upload | PASS |
| Offline regional road calculation | PASS, with network disabled and restored afterward |
| Back / background / process restart / recording restart | PASS |
| Rotation and draft restoration | PASS; Flutter launch restoration and landscape controls fixed |
| Native place search / select result as route point | PASS, with actual Kumily search results |
| Existing recorded route | Loaded all 9 original fixes without changing the saved recording |

Loading a route now frames the actual native road-route polyline, including
multi-stop routes. Confirmed End Ride cancels native navigation, stops live
tracking and returns to Home; cancelling its confirmation leaves the ride active.

The Android lint tool intermittently reports an internal `HardwareIdDetector`
PSI exception while still returning success and producing its report. A clean
lint run also completed without that exception; this is not a claim that every
warning or tooling issue has been resolved.

The Organic Maps routing and recording engines remain unchanged. The small core
map extension adds position updates to existing API markers so RouteOS can move
admin driver markers without deleting them or recentering the map. Other native
changes are confined to the UI/engine bridge, JNI adapter, authenticated HTTP
client, and explicit RouteOS ride lifecycle in NavigationService.
Required map assets and original user routes were preserved. One shared test
route was added through the phone to verify save/reload and cross-driver access.

Not yet verified: an actual multi-turn drive recording/upload, moving turn-by-turn
guidance, rerouting, arrival, audible voice guidance, lock-screen/notification
reopening, and simultaneous two-device admin map tracking. Backend/admin access
and active-ride location reporting were tested, but are not substitutes for that
two-device check. An independent clean clone, production HTTPS deployment,
durable hosted database migration, and production release signing are also not
verified. Alpha 2.4 is a tester release, not a store-signed production build.

Organic Maps limits routing to 102 points. Complete recorded GPS tracks are kept;
long recordings use native simplification anchors for road navigation, which can
differ from the driven track. Android alternative-route metadata/selection is
not exposed by this revision's JNI/Java API; no fake selector is provided. See
`flutter_routeos/README.md` for the exact integration boundaries and limitations.
