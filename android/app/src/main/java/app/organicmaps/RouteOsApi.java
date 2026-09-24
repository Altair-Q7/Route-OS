package app.organicmaps;

import android.content.Context;
import android.location.Location;
import androidx.annotation.NonNull;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.List;
import org.json.JSONArray;
import org.json.JSONObject;

final class RouteOsApi {
  private static final String API = "http://127.0.0.1:8000";
  private RouteOsApi() {}

  static JSONObject login(@NonNull Context context, @NonNull String name) throws Exception {
    JSONObject user = post("/api/v1/auth/login", new JSONObject().put("name", name.trim()));
    context.getSharedPreferences("routeos", Context.MODE_PRIVATE).edit()
           .putLong("driver_id", user.getLong("id"))
           .putString("driver_name", user.getString("name"))
           .putString("role", user.getString("role"))
           .apply();
    return user;
  }

  static void publish(@NonNull Context context, @NonNull String name, @NonNull List<Location> points) throws Exception {
    if (points.size() < 2) throw new IllegalArgumentException("Move far enough to record at least two GPS points");
    publishPoints(context, name, points, "Hub", "Recorded destination");
  }

  static void publishPoints(@NonNull Context context, @NonNull String name, @NonNull List<Location> points,
                            @NonNull String origin, @NonNull String destination) throws Exception {
    long driverId = context.getSharedPreferences("routeos", Context.MODE_PRIVATE).getLong("driver_id", 0);
    if (driverId == 0) {
      String savedName = context.getSharedPreferences("routeos", Context.MODE_PRIVATE).getString("driver_name", "Driver");
      JSONObject user = login(context, savedName == null ? "Driver" : savedName);
      driverId = user.getLong("id");
    }
    if (points.size() < 2) throw new IllegalArgumentException("A route needs at least two points");
    JSONArray trackPoints = new JSONArray();
    for (Location location : points) {
      trackPoints.put(new JSONObject().put("latitude", location.getLatitude())
                                     .put("longitude", location.getLongitude())
                                     .put("timestamp", location.getTime() == 0 ? JSONObject.NULL : location.getTime())
                                     .put("altitude_meters", location.hasAltitude() ? location.getAltitude() : JSONObject.NULL));
    }
    JSONObject track = post("/api/v1/tracks", new JSONObject().put("recorder_id", driverId)
                                                               .put("organic_maps_track_id", "organicmaps-" + System.currentTimeMillis())
                                                               .put("points", trackPoints));
    post("/api/v1/routes", new JSONObject().put("name", name)
                                             .put("recorder_id", driverId)
                                             .put("track_id", track.getLong("id"))
                                             .put("origin", origin)
                                             .put("destination", destination)
                                             .put("hub_latitude", points.get(0).getLatitude())
                                             .put("hub_longitude", points.get(0).getLongitude()));
  }

  static JSONArray getRoutes() throws Exception {
    return getArray("/api/v1/routes");
  }

  static JSONObject getRoute(long routeId) throws Exception {
    return getObject("/api/v1/routes/" + routeId);
  }

  static JSONObject startRide(@NonNull Context context, long routeId, @NonNull String vehicleType,
                              @NonNull String vehicleNumber) throws Exception {
    long driverId = context.getSharedPreferences("routeos", Context.MODE_PRIVATE).getLong("driver_id", 0);
    JSONObject ride = post("/api/v1/rides", new JSONObject().put("driver_id", driverId)
        .put("route_id", routeId).put("vehicle_type", vehicleType).put("vehicle_number", vehicleNumber));
    context.getSharedPreferences("routeos", Context.MODE_PRIVATE).edit()
        .putLong("active_ride_id", ride.getLong("id")).apply();
    return ride;
  }

  static void updateLiveLocation(@NonNull Context context, long rideId, @NonNull Location location) throws Exception {
    long driverId = context.getSharedPreferences("routeos", Context.MODE_PRIVATE).getLong("driver_id", 0);
    JSONObject body = new JSONObject().put("driver_id", driverId)
        .put("latitude", location.getLatitude()).put("longitude", location.getLongitude());
    if (location.hasSpeed()) body.put("speed_mps", Math.max(0, location.getSpeed()));
    if (location.hasBearing()) body.put("bearing", Math.max(0, Math.min(360, location.getBearing())));
    post("/api/v1/rides/" + rideId + "/locations", body);
  }

  static void endRide(@NonNull Context context, long rideId) throws Exception {
    post("/api/v1/rides/" + rideId + "/end", new JSONObject());
    context.getSharedPreferences("routeos", Context.MODE_PRIVATE).edit().remove("active_ride_id").apply();
  }

  static JSONArray getActiveRides() throws Exception {
    return getArray("/api/v1/rides/active");
  }

  static JSONObject getDriverActiveRide(@NonNull Context context) throws Exception {
    long driverId = context.getSharedPreferences("routeos", Context.MODE_PRIVATE).getLong("driver_id", 0);
    return getObject("/api/v1/drivers/" + driverId + "/active-ride");
  }

  static void clearActiveRide(@NonNull Context context) {
    context.getSharedPreferences("routeos", Context.MODE_PRIVATE).edit()
        .remove("active_ride_id").remove("active_route_id").remove("active_route_name")
        .remove("active_destination_lat").remove("active_destination_lon").apply();
  }

  static void logout(@NonNull Context context) {
    context.getSharedPreferences("routeos", Context.MODE_PRIVATE).edit().clear().apply();
  }

  private static JSONArray getArray(String path) throws Exception {
    HttpURLConnection connection = (HttpURLConnection) new URL(API + path).openConnection();
    connection.setConnectTimeout(3000);
    connection.setReadTimeout(5000);
    if (connection.getResponseCode() != 200) throw new IllegalStateException("HTTP " + connection.getResponseCode());
    return new JSONArray(new String(connection.getInputStream().readAllBytes(), StandardCharsets.UTF_8));
  }

  private static JSONObject getObject(String path) throws Exception {
    HttpURLConnection connection = (HttpURLConnection) new URL(API + path).openConnection();
    connection.setConnectTimeout(3000);
    connection.setReadTimeout(5000);
    if (connection.getResponseCode() != 200) throw new IllegalStateException("HTTP " + connection.getResponseCode());
    return new JSONObject(new String(connection.getInputStream().readAllBytes(), StandardCharsets.UTF_8));
  }

  private static JSONObject post(String path, JSONObject body) throws Exception {
    HttpURLConnection connection = (HttpURLConnection) new URL(API + path).openConnection();
    connection.setRequestMethod("POST");
    connection.setRequestProperty("Content-Type", "application/json");
    // A recorded ride uploads thousands of GPS points in one request, so uploads need a longer
    // read timeout than the small GET requests above.
    connection.setConnectTimeout(3000);
    connection.setReadTimeout(15000);
    connection.setDoOutput(true);
    byte[] data = body.toString().getBytes(StandardCharsets.UTF_8);
    try (OutputStream output = connection.getOutputStream()) { output.write(data); }
    java.io.InputStream input = connection.getResponseCode() < 400 ? connection.getInputStream() : connection.getErrorStream();
    String response = new String(input.readAllBytes(), StandardCharsets.UTF_8);
    if (connection.getResponseCode() >= 400) throw new IllegalStateException(response);
    return new JSONObject(response);
  }
}
