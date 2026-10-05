package app.routeos;

import android.content.Context;
import android.location.Location;
import androidx.annotation.NonNull;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.time.Instant;
import java.nio.charset.StandardCharsets;
import java.util.List;
import org.json.JSONArray;
import org.json.JSONObject;

public final class RouteOsApi {
  public static final class ApiException extends IOException {
    public final int status;
    ApiException(int status, String message) { super(message); this.status=status; }
  }
  private static ApiException httpError(HttpURLConnection connection) throws IOException {
    String body=errorBody(connection);
    try { Object detail=new JSONObject(body).opt("detail"); if(detail!=null)body=detail.toString(); } catch(Exception ignored) {}
    return new ApiException(connection.getResponseCode(),body);
  }
  /** Default RouteOS deployment. A local debug server can still be selected in RouteOS settings. */
  public static final String DEFAULT_API = "https://route-os-backend.onrender.com";
  private RouteOsApi() {}

  public static String baseUrl(@NonNull Context context) {
    String saved = context.getSharedPreferences("routeos", Context.MODE_PRIVATE)
        .getString("api_base_url", null);
    if (saved != null && !saved.isEmpty())
      return normalizeBaseUrl(context, saved);
    return DEFAULT_API;
  }

  public static void setBaseUrl(@NonNull Context context, @NonNull String baseUrl) {
    baseUrl = normalizeBaseUrl(context, baseUrl);
    var prefs = context.getSharedPreferences("routeos", Context.MODE_PRIVATE);
    if (baseUrl.equals(baseUrl(context)))
      return;
    if (prefs.getLong("active_ride_id", 0) > 0)
      throw new IllegalStateException("End the ride before changing servers");
    // Bind drafts from older clients to the server that owned their account IDs.
    var drafts = prefs.edit();
    String oldServer = baseUrl(context);
    for (String key : prefs.getAll().keySet())
    {
      String driver = key.equals("planner_draft")      ? Long.toString(prefs.getLong("driver_id", 0))
                    : key.startsWith("planner_draft_") ? key.substring("planner_draft_".length())
                                                       : "";
      if (!driver.matches("[0-9]+"))
        continue;
      String scoped = "planner_draft_" + oldServer + "_" + driver;
      if (!driver.equals("0") && !prefs.contains(scoped))
        drafts.putString(scoped, prefs.getString(key, "{}"));
      drafts.remove(key);
    }
    drafts.apply();
    logout(context);
    context.getSharedPreferences("routeos", Context.MODE_PRIVATE).edit()
        .putString("api_base_url", baseUrl).apply();
  }

  static String normalizeBaseUrl(@NonNull Context context, @NonNull String baseUrl)
  {
    java.net.URI uri;
    try
    {
      uri = new java.net.URI(baseUrl.trim()).normalize();
    }
    catch (java.net.URISyntaxException error)
    {
      throw new IllegalArgumentException("Enter a valid RouteOS server URL", error);
    }
    if (uri.getHost() == null || uri.getUserInfo() != null || uri.getQuery() != null || uri.getFragment() != null
        || uri.getPort() == 0 || uri.getPort() > 65535)
      throw new IllegalArgumentException("Enter a valid RouteOS server URL without credentials, query or fragment");
    boolean localDebug = (context.getApplicationInfo().flags & android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0
                      && "http".equalsIgnoreCase(uri.getScheme())
                      && ("127.0.0.1".equals(uri.getHost()) || "10.0.2.2".equals(uri.getHost()));
    if (!"https".equalsIgnoreCase(uri.getScheme()) && !localDebug)
      throw new IllegalArgumentException("RouteOS requires HTTPS");
    String path = uri.getRawPath();
    while (path.endsWith("/"))
      path = path.substring(0, path.length() - 1);
    return uri.getScheme().toLowerCase(java.util.Locale.ROOT) + "://"
  + uri.getRawAuthority().toLowerCase(java.util.Locale.ROOT) + path;
  }

  private static String token(@NonNull Context context) {
    return RouteOsCredentials.read(context);
  }

  public static JSONObject login(@NonNull Context context, @NonNull String name) throws Exception {
    return login(context, name, null);
  }

  public static JSONObject login(@NonNull Context context, @NonNull String name, String password) throws Exception {
    var prefs=context.getSharedPreferences("routeos",0);
    name = name.trim();
    if(prefs.getLong("active_ride_id",0)>0 && !name.equalsIgnoreCase(prefs.getString("driver_name","")))
      throw new IllegalStateException("Sign in as the active ride's driver, or end the ride before switching accounts");
    JSONObject user = post(context, "/api/v1/auth/login", new JSONObject().put("name", name.trim()).put("password", password));
    if (prefs.getLong("active_ride_id", 0) > 0 && user.getLong("id") != prefs.getLong("driver_id", 0))
      throw new IllegalStateException("Sign in as the active ride's driver");
    android.content.SharedPreferences.Editor editor =
        context.getSharedPreferences("routeos", Context.MODE_PRIVATE).edit()
            .putLong("driver_id", user.getLong("id"))
            .putString("driver_name", user.getString("name"))
            .putString("role", user.getString("role"));
    String freshToken = user.optString("auth_token", null);
    if (freshToken != null && !freshToken.isEmpty()) RouteOsCredentials.store(context, freshToken);
    editor.apply();
    if (prefs.getLong("active_ride_id", 0) > 0)
      RouteOsLocationUploader.get(context).start();
    return user;
  }

  public static void publish(@NonNull Context context, @NonNull String name, @NonNull List<Location> points) throws Exception {
    if (points.size() < 2) throw new IllegalArgumentException("Move far enough to record at least two GPS points");
    publishPoints(context, name, points, "Hub", "Recorded destination", "recorded");
  }

  public static void publishPoints(@NonNull Context context, @NonNull String name, @NonNull List<Location> points,
                            @NonNull String origin, @NonNull String destination) throws Exception {
    publishPoints(context, name, points, origin, destination, "drawn");
  }

  public static void publishPoints(@NonNull Context context, @NonNull String name, @NonNull List<Location> points,
                            @NonNull String origin, @NonNull String destination, @NonNull String routeType) throws Exception {
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
                                     .put("timestamp", location.getTime() == 0 ? JSONObject.NULL : Instant.ofEpochMilli(location.getTime()).toString())
                                     .put("altitude_meters", location.hasAltitude() ? location.getAltitude() : JSONObject.NULL));
    }
    JSONObject track = post(context, "/api/v1/tracks", new JSONObject().put("recorder_id", driverId)
                                                                .put("organic_maps_track_id", "organicmaps-" + System.currentTimeMillis())
                                                                .put("points", trackPoints));
    post(context, "/api/v1/routes", new JSONObject().put("name", name)
                                             .put("recorder_id", driverId)
                                             .put("track_id", track.getLong("id"))
                                             .put("origin", origin)
                                             .put("destination", destination)
                                             .put("route_type", routeType)
                                             .put("hub_latitude", points.get(0).getLatitude())
                                             .put("hub_longitude", points.get(0).getLongitude()));
  }

  public static JSONArray getRoutes(@NonNull Context context) throws Exception {
    long driverId = context.getSharedPreferences("routeos", Context.MODE_PRIVATE).getLong("driver_id", 0);
    return getArray(context, "/api/v1/routes?driver_id=" + driverId);
  }

  public static JSONObject renameRoute(@NonNull Context context, long routeId, @NonNull String name) throws Exception {
    long driverId = context.getSharedPreferences("routeos", Context.MODE_PRIVATE).getLong("driver_id", 0);
    return patch(context, "/api/v1/routes/" + routeId, new JSONObject().put("driver_id", driverId).put("name", name));
  }

  public static JSONObject deleteRoute(@NonNull Context context, long routeId) throws Exception {
    long driverId = context.getSharedPreferences("routeos", Context.MODE_PRIVATE).getLong("driver_id", 0);
    return delete(context, "/api/v1/routes/" + routeId + "?driver_id=" + driverId);
  }

  public static JSONObject setFavorite(@NonNull Context context, long routeId, boolean favorite) throws Exception {
    long driverId = context.getSharedPreferences("routeos", Context.MODE_PRIVATE).getLong("driver_id", 0);
    if (favorite)
      return post(context, "/api/v1/routes/" + routeId + "/favorite", new JSONObject().put("driver_id", driverId));
    return delete(context, "/api/v1/routes/" + routeId + "/favorite?driver_id=" + driverId);
  }

  public static JSONObject markRecent(@NonNull Context context, long routeId) throws Exception {
    long driverId = context.getSharedPreferences("routeos", Context.MODE_PRIVATE).getLong("driver_id", 0);
    return post(context, "/api/v1/routes/" + routeId + "/recent", new JSONObject().put("driver_id", driverId));
  }

  public static JSONObject clearRecent(@NonNull Context context, long routeId) throws Exception {
    long driverId = context.getSharedPreferences("routeos", Context.MODE_PRIVATE).getLong("driver_id", 0);
    return delete(context, "/api/v1/routes/" + routeId + "/recent?driver_id=" + driverId);
  }

  public static JSONObject shareRoute(@NonNull Context context, long routeId, long recipientId) throws Exception {
    long driverId = context.getSharedPreferences("routeos", Context.MODE_PRIVATE).getLong("driver_id", 0);
    JSONObject body = new JSONObject().put("driver_id", driverId);
    body.put("recipient_id", recipientId > 0 ? recipientId : JSONObject.NULL);
    return post(context, "/api/v1/routes/" + routeId + "/share", body);
  }

  public static JSONObject getRoute(@NonNull Context context, long routeId) throws Exception {
    return getObject(context, "/api/v1/routes/" + routeId);
  }

  public static JSONObject startRide(@NonNull Context context, long routeId, @NonNull String vehicleType,
                              @NonNull String vehicleNumber) throws Exception {
    long driverId = context.getSharedPreferences("routeos", Context.MODE_PRIVATE).getLong("driver_id", 0);
    JSONObject ride = post(context, "/api/v1/rides", new JSONObject().put("driver_id", driverId)
        .put("route_id", routeId).put("vehicle_type", vehicleType).put("vehicle_number", vehicleNumber));
    context.getSharedPreferences("routeos", Context.MODE_PRIVATE)
        .edit()
        .putLong("active_ride_id", ride.getLong("id"))
        .putString("tracking_state", "waiting_gps")
        .remove("tracking_last_upload")
        .apply();
    return ride;
  }

  public static JSONObject updateLiveLocation(@NonNull Context context, long rideId, @NonNull Location location) throws Exception {
    long driverId = context.getSharedPreferences("routeos", Context.MODE_PRIVATE).getLong("driver_id", 0);
    JSONObject body = new JSONObject().put("driver_id", driverId)
        .put("latitude", location.getLatitude()).put("longitude", location.getLongitude());
    if (location.hasSpeed()) body.put("speed_mps", Math.max(0, location.getSpeed()));
    if (location.hasBearing()) body.put("bearing", Math.max(0, Math.min(360, location.getBearing())));
    return post(context, "/api/v1/rides/" + rideId + "/locations", body);
  }

  public static void endRide(@NonNull Context context, long rideId) throws Exception {
    long driverId = context.getSharedPreferences("routeos", Context.MODE_PRIVATE).getLong("driver_id", 0);
    try
    {
      post(context, "/api/v1/rides/" + rideId + "/end", new JSONObject().put("driver_id", driverId));
    }
    catch (ApiException missingRide)
    {
      if (missingRide.status != 404)
        throw missingRide;
    }
    clearActiveRide(context);
  }

  public static JSONObject arriveRide(@NonNull Context context, long rideId) throws Exception {
    long driverId = context.getSharedPreferences("routeos", Context.MODE_PRIVATE).getLong("driver_id", 0);
    JSONObject arrived = post(context, "/api/v1/rides/" + rideId + "/arrive", new JSONObject().put("driver_id", driverId));
    clearActiveRide(context);
    return arrived;
  }

  public static JSONArray getActiveRides(@NonNull Context context) throws Exception {
    return getArray(context, "/api/v1/rides/active");
  }
  public static JSONObject getOwnActiveRide(@NonNull Context context) throws Exception {
    return getObject(context, "/api/v1/drivers/"+context.getSharedPreferences("routeos",0).getLong("driver_id",0)+"/active-ride");
  }

  public static JSONObject getDriverActiveRide(@NonNull Context context) throws Exception {
    long driverId = context.getSharedPreferences("routeos", Context.MODE_PRIVATE).getLong("driver_id", 0);
    return getObject(context, "/api/v1/drivers/" + driverId + "/active-ride");
  }

  public static void clearActiveRide(@NonNull Context context) {
    context.getSharedPreferences("routeos", Context.MODE_PRIVATE)
        .edit()
        .remove("active_ride_id")
        .remove("active_route_id")
        .remove("active_route_name")
        .remove("active_destination_lat")
        .remove("active_destination_lon")
        .remove("ride_arrived")
        .remove("tracking_state")
        .remove("tracking_last_upload")
        .remove("tracking_pending")
        .apply();
  }

  public static void logout(@NonNull Context context) {
    RouteOsCredentials.clear(context);
    android.content.SharedPreferences prefs =
        context.getSharedPreferences("routeos", Context.MODE_PRIVATE);
    android.content.SharedPreferences.Editor editor = prefs.edit();
    for (String key : prefs.getAll().keySet())
      if (!key.equals("api_base_url") && !key.startsWith("planner_draft"))
        editor.remove(key);
    editor.apply();
  }

  /** Reads a whole stream without InputStream#readAllBytes, which is only available from API 33. */
  public static String readFully(@NonNull InputStream input) throws IOException {
    ByteArrayOutputStream buffer = new ByteArrayOutputStream();
    byte[] chunk = new byte[8192];
    for (int read = input.read(chunk); read != -1; read = input.read(chunk))
      buffer.write(chunk, 0, read);
    return new String(buffer.toByteArray(), StandardCharsets.UTF_8);
  }

  private static String errorBody(HttpURLConnection connection) {
    try {
      InputStream input = connection.getErrorStream();
      if (input == null) return "HTTP " + connection.getResponseCode();
      String body = readFully(input);
      return body.isEmpty() ? "HTTP " + connection.getResponseCode() : body;
    } catch (IOException ignored) {
      return "request failed";
    }
  }

  private static void attachToken(@NonNull Context context, HttpURLConnection connection) {
    String authToken = token(context);
    if (authToken != null && !authToken.isEmpty())
      connection.setRequestProperty("Authorization", "Bearer " + authToken);
  }

  private static JSONArray getArray(@NonNull Context context, String path) throws Exception {
    HttpURLConnection connection = (HttpURLConnection) new URL(baseUrl(context) + path).openConnection();
    try {
      connection.setInstanceFollowRedirects(false);
      connection.setConnectTimeout(3000);
      connection.setReadTimeout(5000);
      attachToken(context, connection);
      if (connection.getResponseCode() != 200) throw httpError(connection);
      return new JSONArray(readFully(connection.getInputStream()));
    } finally {
      connection.disconnect();
    }
  }

  private static JSONObject getObject(@NonNull Context context, String path) throws Exception {
    HttpURLConnection connection = (HttpURLConnection) new URL(baseUrl(context) + path).openConnection();
    try {
      connection.setInstanceFollowRedirects(false);
      connection.setConnectTimeout(3000);
      connection.setReadTimeout(5000);
      attachToken(context, connection);
      if (connection.getResponseCode() != 200) throw httpError(connection);
      return new JSONObject(readFully(connection.getInputStream()));
    } finally {
      connection.disconnect();
    }
  }

  public static JSONObject post(@NonNull Context context, String path, JSONObject body) throws Exception {
    return post(baseUrl(context), token(context), path, body);
  }

  static JSONObject postForDriver(Context context, String server, long driverId, String path, JSONObject body)
      throws Exception
  {
    if (!server.equals(baseUrl(context))
        || driverId != context.getSharedPreferences("routeos", 0).getLong("driver_id", 0))
      throw new IllegalStateException("RouteOS session changed");
    return post(server, token(context), path, body);
  }

  private static JSONObject post(String server, String authToken, String path, JSONObject body) throws Exception
  {
    HttpURLConnection connection = (HttpURLConnection) new URL(server + path).openConnection();
    try {
      connection.setInstanceFollowRedirects(false);
      connection.setRequestMethod("POST");
      connection.setRequestProperty("Content-Type", "application/json");
      if (authToken != null && !authToken.isEmpty())
        connection.setRequestProperty("Authorization", "Bearer " + authToken);
      // A recorded ride uploads thousands of GPS points in one request, so uploads need a longer
      // read timeout than the small GET requests above.
      connection.setConnectTimeout(3000);
      connection.setReadTimeout(15000);
      connection.setDoOutput(true);
      byte[] data = body.toString().getBytes(StandardCharsets.UTF_8);
      try (OutputStream output = connection.getOutputStream()) { output.write(data); }
      if (connection.getResponseCode() < 200 || connection.getResponseCode() >= 300)
        throw httpError(connection);
      return new JSONObject(readFully(connection.getInputStream()));
    } finally {
      connection.disconnect();
    }
  }

  private static JSONObject patch(@NonNull Context context, String path, JSONObject body) throws Exception {
    return requestWithBody(context, "PATCH", path, body);
  }

  private static JSONObject delete(@NonNull Context context, String path) throws Exception {
    HttpURLConnection connection = (HttpURLConnection) new URL(baseUrl(context) + path).openConnection();
    try {
      connection.setInstanceFollowRedirects(false);
      connection.setRequestMethod("DELETE");
      connection.setConnectTimeout(3000);
      connection.setReadTimeout(5000);
      attachToken(context, connection);
      if (connection.getResponseCode() < 200 || connection.getResponseCode() >= 300)
        throw httpError(connection);
      return new JSONObject(readFully(connection.getInputStream()));
    } finally {
      connection.disconnect();
    }
  }

  private static JSONObject requestWithBody(@NonNull Context context, @NonNull String method, @NonNull String path, @NonNull JSONObject body) throws Exception {
    HttpURLConnection connection = (HttpURLConnection) new URL(baseUrl(context) + path).openConnection();
    try {
      connection.setInstanceFollowRedirects(false);
      connection.setRequestMethod(method);
      connection.setRequestProperty("Content-Type", "application/json");
      attachToken(context, connection);
      connection.setConnectTimeout(3000);
      connection.setReadTimeout(5000);
      connection.setDoOutput(true);
      try (OutputStream output = connection.getOutputStream()) { output.write(body.toString().getBytes(StandardCharsets.UTF_8)); }
      if (connection.getResponseCode() < 200 || connection.getResponseCode() >= 300)
        throw httpError(connection);
      return new JSONObject(readFully(connection.getInputStream()));
    } finally {
      connection.disconnect();
    }
  }
}
