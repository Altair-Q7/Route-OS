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
- Native GPS can supply a route point or recenter the map. Navigation rebuilds
  from the actual current position before creating the backend ride.
- **Draw Route** uses Flutter controls over the native map. Tap to add ordered
  start/via/destination points; move, insert, delete, reorder, clear, undo and redo
  recalculate through Organic Maps. Planned routes save their waypoint definition
  and native distance/time; they are not fabricated GPS recordings.
- **Record Route** captures GPS from the foreground recording service, including
  while the map activity is not in the foreground.
- Saved routes are shared globally, so every signed-in driver sees them.
- Vehicle type and number are stored only on a ride; there is no fleet module.
- During a ride the driver uploads the latest GPS location every five seconds.
  The admin map polls active rides and stops showing a driver after End Ride.
- The backend stores users, tracks, routes, rides, and live locations only.

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
adb install -r android/app/build/outputs/apk/google/debug/OrganicMaps-*-google-debug.apk
adb shell am start -n app.organicmaps.debug/app.organicmaps.DownloadResourcesActivity
python3 tools/routeos-device-ui.py --expect RouteOS
```

`tools/routeos-device-ui.py --tap LABEL` uses Android accessibility labels to
exercise the real installed UI. Wait for installation and each assertion to
finish; do not run concurrent ADB interaction scripts. Road routing requires the
relevant regional offline map. Actual turn-by-turn/rerouting and multi-turn
recording still require a physical driving test.

## Verification on 2 October 2026

The installed Android debug build runs actual Flutter product UI with the native
Organic Maps platform view on the connected Nothing A142. Regional Kerala and
Tamil Nadu maps are installed; these checks do not substitute screenshots or a
network routing service for the map engine.

| Check | Result |
| --- | --- |
| Clean Android debug assembly | PASS |
| Android lint | Task succeeds; 0 errors, 436 warnings; see tooling caveat below |
| Flutter analysis | No issues |
| Flutter planner tests | 5 passed |
| Backend tests | 36 passed, 0 failed |
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

Organic Maps' core `libs/` code and `TrackRecordingService` were not modified.
Changes to native code are the UI/engine bridge, JNI adapters, shared authenticated
HTTP client, and explicit RouteOS ride-ending integration in NavigationService.
Required map assets and original user routes were preserved. One shared test
route was added through the phone to verify save/reload and cross-driver access.

Not yet verified: an actual multi-turn drive recording/upload, moving turn-by-turn
guidance, rerouting, arrival, audible voice guidance, lock-screen/notification
reopening, and simultaneous two-device admin map tracking. Backend/admin access
and active-ride location reporting were tested, but are not substitutes for that
two-device check. An independent clean clone, production HTTPS deployment and
release signing are also not verified. This is a development MVP, not a signed
beta release.

Organic Maps limits routing to 102 points. Complete recorded GPS tracks are kept;
long recordings use native simplification anchors for road navigation, which can
differ from the driven track. Android alternative-route metadata/selection is
not exposed by this revision's JNI/Java API; no fake selector is provided. See
`flutter_routeos/README.md` for the exact integration boundaries and limitations.
