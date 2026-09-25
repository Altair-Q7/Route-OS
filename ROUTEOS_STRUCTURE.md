# RouteOS structure

RouteOS is layered on top of Organic Maps without moving or replacing the map engine.

## Android

- `android/app/src/main/java/app/organicmaps/` — Organic Maps application host, map UI, search, location, and native navigation.
- `android/app/src/main/java/app/routeos/` — RouteOS screens, styling, API client, login/session state, and route-recording session state.
- `android/app/src/main/java/app/organicmaps/MwmActivity.java` — the small integration boundary that opens the native map/navigation surface and RouteOS overlays.
- `android/app/src/main/java/app/organicmaps/location/TrackRecordingService.java` — Organic Maps track recorder with the RouteOS recording-session bridge.
- `android/libs/routing/.../NavigationService.java` — Organic Maps navigation service with the minimal background live-location/end-ride bridge.

## Backend

- `backend/` — the minimal RouteOS service for users, tracks, routes, rides, and live driver locations.

Organic Maps remains responsible for maps, GPS, routing, navigation, ETA, voice guidance, and rerouting. RouteOS owns the saved-route and ride workflow around those capabilities.
