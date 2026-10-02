# RouteOS Flutter shell

This module is the RouteOS product UI layer. Organic Maps remains the native map, GPS, routing,
navigation, voice guidance, and track-recording engine.

## Validate the Flutter UI

```bash
flutter analyze
flutter test
```

## Build the Android host integration

The Organic Maps project uses AGP 9, while Flutter's module Gradle plugin currently expects a
legacy Android extension. Build this module as an AAR instead of loading that plugin into the
Organic Maps Gradle graph:

```bash
flutter build aar --no-debug --no-profile --release --build-number=1 --output="$PWD/build"
cd ../android
./gradlew -Parm64 :app:assembleGoogleDebug
```

The Android app consumes `build/host/outputs/repo`. The generated build directory is intentionally
not source-controlled; regenerate it after a clean checkout or after changing Dart code.

The launcher enters the Flutter shell hosted by `MwmActivity`. The original map controller
owns the existing Organic Maps MapView, now presented by a hybrid-composition platform view.
Do not run this module as a standalone Flutter app: its native map factory exists in the host.

Source boundaries:

- `lib/app/`: theme and application shell.
- `lib/core/`: versioned platform channel.
- `lib/map/`: real Android platform view, not a Dart map renderer.
- `lib/home/`: RouteOS product screens and dialogs.
- `lib/routing/`: waypoint ordering, editing history and planner state; no road geometry.
- `android/app/.../app/routeos/bridge/`: native map/engine adapter in the host repository.
- `android/sdk/.../app/routeos/`: authenticated API client and Android Keystore session storage.

The channel envelope is `{version: 1, data: ...}`. Methods include `calculate`, `center`, `zoom`,
`location`, `search`, `record`, `record.stop`, `record.cancel`, `ride.start`, `ride.end`,
`ride.restore`, route management, and draft persistence. Events include `map.tap`,
`map.point.selected`, `route.ready`, `route.failed`, native search results, navigation progress,
and recording progress. Unsupported commands/versions return explicit errors.

Organic Maps supports **100 intermediate points + start + destination**, not unlimited points.
The client and server enforce that actual engine limit. Optimise previews use geographic
2-opt ordering with fixed endpoints, not a claim of optimal driving time. OM computes all roads.
Moving is select-point → Move on map → tap the new position; reordering uses the point list.

Recorded routes retain their complete GPS track on the backend and import that original track
into Organic Maps for display. For navigation, recordings exceeding the route-point limit use
Organic Maps' simplification helper to choose at most 101 ordered anchors, leaving room for the
current GPS start. Routing between anchors can differ from the original driven path; this is
not a promise of exact track-following. Planned routes keep their explicit ordered waypoints.
Navigation first rebuilds from the actual native GPS position before creating a backend ride.

The checked-out C++ `RoutingSession` has alternative-route support, but this revision's Android
`Framework` JNI and `RoutingController` expose neither alternative metadata nor a selection
method. No artificial alternative-route selector is presented. Ordering optimisation is a
RouteOS geographic ordering preview; it is not traffic-aware or minimum-driving-time routing.

Activity recreation retains the Flutter entry independently of the consumed launch intent.
The locally persisted planner also retains its page and editing history; it recalculates
through Organic Maps when the planner is restored. Existing Organic Maps configuration-change
handling remains unchanged, rather than avoiding recreation with additional manifest flags.
