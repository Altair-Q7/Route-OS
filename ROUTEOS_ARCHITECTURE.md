# RouteOS Architecture Documentation

## Overview

RouteOS is a **driver/ride management layer** built on top of **Organic Maps** (an open-source offline maps & GPS application). RouteOS does not replace the map engine - it extends it with ride/route management, driver tracking, and admin features.

```
┌─────────────────────────────────────────────────────────────────┐
│                        ROUTEOS LAYER                              │
├──────────────────┬──────────────────────┬───────────────────────┤
│   Flutter UI     │   Android Native     │    Python Backend     │
│  (Driver App)    │  (Integration/Overlays)│  (REST API / DB)    │
└────────┬─────────┴──────────┬───────────┴──────────┬────────────┘
         │                    │                      │
         ▼                    ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ORGANIC MAPS CORE                            │
├─────────────────────────────────────────────────────────────────┤
│  Map Rendering  │  GPS/Location  │  Routing/Navigation  │ Data  │
│  (OpenGL/Vulkan)│  (Platform)    │  (A*/Contraction)    │ (MWM) │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Python Backend (`backend/`)
**Purpose**: REST API for user authentication, route/ride management, live driver tracking.

**Key Files**:
- `app.py` (1036 lines) - Main FastAPI application with all endpoints
- `provision_password.py` - Password hashing utility
- `tests/` - 9 test modules covering auth, routes, rides, permissions, database

**Data Model**:
```
User (driver/admin) ←→ Route (saved planned routes) ←→ Ride (active driver session)
                          ↓                              ↓
                   Waypoints (start/via/end)       Live GPS locations
                   Distance/time estimates         Ride state (active/ended)
```

**API Endpoints**:
- `/auth/*` - Login, session management, quick-login for demo
- `/api/v1/routes/*` - CRUD for planned routes (shared globally)
- `/api/v1/rides/*` - Start/end rides, vehicle info, live location upload
- `/api/v1/admin/*` - Admin dashboard: active rides, driver locations

**Key Design Decisions**:
- SQLite database (single file `routeos.db`) for simplicity
- JWT-style session tokens in `Authorization` header
- Quick-login via `ROUTEOS_DEVELOPMENT_AUTH=1` env var (demo accounts)
- Live location uploaded every 5 seconds during active ride
- Admin polls active rides for live tracking map

---

### 2. Flutter UI (`flutter_routeos/lib/`)
**Purpose**: Modern declarative UI for driver-facing features (route planner, home, navigation).

**Key Files**:
| File | Lines | Purpose |
|------|-------|---------|
| `main.dart` | 12 | App entry point, error handling bridge |
| `app/app.dart` | 31 | MaterialApp setup, routing |
| `core/bridge.dart` | 10 | Dart↔Native method channel communication |
| `home/home.dart` | 1625 | Main driver dashboard, route list, ride actions |
| `map/native_map.dart` | 28 | Platform view embedding Organic Maps native surface |
| `routing/planner.dart` | 232 | Route planning logic, waypoint management |

**Flutter↔Native Bridge** (`core/bridge.dart`):
```dart
// Dart calls native via MethodChannel
static const MethodChannel _channel = MethodChannel('routeos/native');

// Example: Request route calculation from Organic Maps engine
final result = await _channel.invokeMethod('calculateRoute', {
  'waypoints': waypoints.map((w) => {'lat': w.lat, 'lon': w.lon}).toList(),
});
```

**State Management**: Simple `setState` + `ChangeNotifier` (no Riverpod/Bloc yet)

**Integration Points**:
- `NativeMapView` - Embeds Organic Maps `MwmActivity` as Android PlatformView
- Route calculation delegated to native via bridge
- GPS location from native `TrackRecordingService`
- Navigation controlled by native `NavigationService`

---

### 3. Android Native Layer (`android/app/src/main/java/app/routeos/`)
**Purpose**: Android Activities/Overlays that host Flutter UI and integrate with Organic Maps.

**File Responsibilities**:

| File | Lines | Role |
|------|-------|------|
| `RouteOsUi.java` | 150 | Shared colors, view factories, UI constants |
| `RouteOsLoginActivity.java` | 81 | Quick-login screen (demo accounts) |
| `RouteOsHomeOverlay.java` | 441 | Main driver home: route list, start ride, admin access |
| `RouteOsRoutesActivity.java` | 353 | Saved routes list, delete, select for ride |
| `RouteOsSearchActivity.java` | 80 | Place search (delegates to OM native search) |
| `RouteOsVehicleActivity.java` | 93 | Vehicle type/number entry before starting ride |
| `RouteOsTrackPreview.java` | 85 | Preview recorded track before saving as route |
| `RouteOsNavigationOverlay.java` | 300 | Active ride UI: ETA, end ride, live location status |
| `RouteOsAdminOverlay.java` | 213 | Admin map: shows all active drivers' live locations |
| `RouteOsRecordingSession.java` | 45 | Bridge to native GPS recording service |
| `RouteOsFlutterHost.java` | 405 | Hosts Flutter engine, manages PlatformView, bridge |
| `RouteOsApi.java` (SDK) | 327 | Authenticated HTTP client for backend API |
| `RouteOsCredentials.java` (SDK) | 50 | Token storage/retrieval |

**Key Integration**: `MwmActivity.java` (2985 lines) - **The central integration point**
- Hosts both native Organic Maps fragments AND Flutter PlatformView
- Manages RouteOS overlay lifecycle (home, navigation, admin)
- Handles ride state machine: idle → vehicle selection → active ride → ended
- Coordinates with `TrackRecordingService` for GPS during recording
- Coordinates with `NavigationService` for turn-by-turn + live location upload

---

### 4. Modified Organic Maps Integration Points

#### `MwmActivity.java` (2985 lines) - **Primary Integration Hub**
```java
// RouteOS state managed in MwmActivity:
private boolean mRouteOsUiActive = false;
private FrameLayout mRouteOsOverlay;
private RouteOsHomeOverlay mRouteOsHome;
private RouteOsNavigationOverlay mRouteOsNavigation;
private RouteOsAdminOverlay mRouteOsAdmin;
private RouteOsFlutterHost mRouteOsFlutter;
private long mRouteOsActiveRideId = 0;
private boolean mRouteOsEndingRide = false;

// Ride lifecycle methods:
private void showRouteOsFlutter() { ... }
private void startRouteOsRide(long routeId, String vehicleType, String vehicleNumber) { ... }
private void endRouteOsRide() { ... }
private void uploadRouteOsLocation(Location location) { ... }  // Every 5 seconds
```

#### `TrackRecordingService.java` (264 lines) - **GPS Recording Bridge**
```java
// RouteOS recording session receives GPS from native recorder:
import app.routeos.RouteOsRecordingSession;

@Override
public void onLocationChanged(Location location) {
    RouteOsRecordingSession.add(location);  // Forward to RouteOS Flutter UI
    // ... existing OM track recording logic
}
```

#### `NavigationService.java` (425 lines) - **Navigation + Live Location Bridge**
```java
// During active RouteOS ride, uploads live location every 5 seconds:
private long mRouteOsLastLocationUpload = 0;

private void uploadRouteOsLocation(Location location) {
    long now = System.currentTimeMillis();
    if (now - mRouteOsLastLocationUpload < 5000) return;  // Throttle
    
    long rideId = getSharedPreferences("routeos", MODE_PRIVATE).getLong("active_ride_id", 0);
    // POST to /api/v1/rides/{rideId}/locations
}

// Ride arrival doesn't auto-end business ride:
private void arriveRouteOsRide() {
    // Mark arrived but keep location reporting alive
    getSharedPreferences("routeos", MODE_PRIVATE).edit().putBoolean("ride_arrived", true).apply();
}
```

---

## Data Flow Examples

### Flow 1: Driver Creates Planned Route
```
1. Flutter: User taps "Draw Route" → adds waypoints on map
2. Flutter: Calls bridge.calculateRoute(waypoints)
3. Native (MwmActivity): Invokes Organic Maps Router C++
4. Native: Returns route geometry (polyline), distance, time
5. Flutter: Displays route preview
6. User taps "Save" → Flutter calls bridge.saveRoute(name, waypoints, geometry)
7. Native (RouteOsApi): POST /api/v1/routes → Backend stores in SQLite
8. Backend: Returns route ID → All drivers see it in their route list
```

### Flow 2: Driver Starts Ride
```
1. Flutter: User selects saved route → taps "Start Ride"
2. Flutter: Shows VehicleActivity (type + number)
3. Flutter: Calls bridge.startRide(routeId, vehicleType, vehicleNumber)
4. Native (MwmActivity): 
   - Stores ride_id, driver_id in SharedPreferences
   - Requests Organic Maps navigation to route destination
   - Shows RouteOsNavigationOverlay
5. NavigationService: Begins turn-by-turn guidance
6. NavigationService: Every 5s uploads GPS to /api/v1/rides/{id}/locations
7. Admin: Polls /api/v1/admin/active-rides → sees driver on map
```

### Flow 3: Admin Tracks Drivers
```
1. Flutter: Admin logs in → sees AdminOverlay
2. AdminOverlay: Calls bridge.getActiveRides()
3. Native (RouteOsApi): GET /api/v1/admin/active-rides
4. Backend: Returns [{ride_id, driver_name, lat, lon, vehicle, updated_at}, ...]
5. Flutter: Renders markers on NativeMapView for each driver
6. Repeats every 5-10 seconds via timer
```

---

## Integration Boundaries

| Boundary | Direction | Mechanism |
|----------|-----------|-----------|
| Flutter → Native | Dart calls native | `MethodChannel('routeos/native')` |
| Native → Flutter | Native pushes to Dart | `RouteOsFlutterHost` + `MethodChannel` |
| Native → Backend | Java HTTP calls | `RouteOsApi` (OkHttp + JWT auth) |
| Backend → Native | Polling only | Native polls `/admin/active-rides` |
| OM Core → RouteOS | Callbacks | `TrackRecordingService`, `NavigationService` |

---

## Limitations & Known Constraints

1. **Routing**: Organic Maps limits to 102 points; long recordings use simplification anchors
2. **Alternative Routes**: Not exposed via current JNI/Java API
3. **iOS**: No RouteOS implementation yet (Android only)
4. **Offline**: Requires regional map downloads (MWM files) for routing
5. **Clean Build**: Not yet verified from independent clone
6. **Production**: No HTTPS/release signing verified

---

## File Ownership Summary

| Directory | Owner | Description |
|-----------|-------|-------------|
| `backend/` | RouteOS | Pure Python FastAPI service |
| `flutter_routeos/lib/` | RouteOS | Flutter UI (Dart) |
| `android/app/src/main/java/app/routeos/` | RouteOS | Android overlays, activities, bridge |
| `android/sdk/src/main/java/app/routeos/` | RouteOS | SDK-level API client |
| `android/app/src/main/java/app/organicmaps/MwmActivity.java` | **Shared** | OM main activity + RouteOS integration |
| `android/app/src/main/java/app/organicmaps/location/TrackRecordingService.java` | **Shared** | OM GPS recorder + RouteOS bridge |
| `android/libs/routing/src/main/java/app/organicmaps/routing/NavigationService.java` | **Shared** | OM navigation + RouteOS live location |

---

## Development Workflow

```bash
# Backend
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
ROUTEOS_DEVELOPMENT_AUTH=1 .venv/bin/uvicorn app:app --reload

# Flutter (rebuild AAR after Dart changes)
bash tools/build-routeos-flutter-aar.sh

# Android
cd android
./gradlew -Parm64 :app:assembleGoogleDebug

# Device test
adb install -r app/build/outputs/apk/google/debug/OrganicMaps-*-google-debug.apk
adb shell am start -n app.organicmaps.debug/app.organicmaps.DownloadResourcesActivity
python3 tools/routeos-device-ui.py --expect RouteOS
```

---

## Future Extension Points

1. **iOS Support**: Replicate Android integration in `iphone/` using Swift/Obj-C++
2. **Fleet Management**: Add vehicle/driver registry, assignment logic
3. **Offline Sync**: Queue ride data when offline, sync when online
4. **Advanced Routing**: Expose alternative routes, avoidances, vehicle profiles
5. **Web Admin**: React/Vue dashboard replacing Flutter admin overlay
6. **Analytics**: Ride metrics, driver performance, route optimization