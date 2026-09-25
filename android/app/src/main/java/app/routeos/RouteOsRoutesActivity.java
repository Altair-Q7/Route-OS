package app.routeos;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import androidx.annotation.Nullable;
import app.organicmaps.MwmActivity;
import app.organicmaps.MwmApplication;
import app.organicmaps.sdk.bookmarks.data.BookmarkManager;
import java.io.File;
import java.io.FileOutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.json.JSONArray;
import org.json.JSONObject;

/** Image-spec RouteOS route picker backed by real shared tracks. */
public final class RouteOsRoutesActivity extends Activity {
  private static final String API = "http://127.0.0.1:8000";
  private final ExecutorService executor = Executors.newSingleThreadExecutor();
  private final ArrayList<JSONObject> routes = new ArrayList<>();
  private LinearLayout routeList;
  private LinearLayout filters;
  private EditText search;
  private int selected = -1;
  private String routeFilter = "All";

  @Override public void onCreate(@Nullable Bundle state) {
    super.onCreate(state);
    getWindow().setStatusBarColor(RouteOsUi.BG);
    getWindow().setNavigationBarColor(Color.rgb(6, 11, 16));
    LinearLayout root = new LinearLayout(this);
    root.setOrientation(LinearLayout.VERTICAL);
    root.setPadding(RouteOsUi.dp(this, 14), RouteOsUi.dp(this, 18), RouteOsUi.dp(this, 14), RouteOsUi.dp(this, 12));
    root.setBackgroundColor(RouteOsUi.BG);

    LinearLayout top = new LinearLayout(this); top.setGravity(Gravity.CENTER_VERTICAL);
    TextView back = RouteOsUi.text(this, "‹", 40, Color.WHITE, false); back.setGravity(Gravity.CENTER); RouteOsUi.pressable(back, this::finish);
    top.addView(back, new LinearLayout.LayoutParams(RouteOsUi.dp(this, 48), RouteOsUi.dp(this, 54)));
    TextView heading = RouteOsUi.text(this, "Select Route", 20, Color.WHITE, true); heading.setGravity(Gravity.CENTER);
    top.addView(heading, new LinearLayout.LayoutParams(0, RouteOsUi.dp(this, 54), 1));
    top.addView(new View(this), new LinearLayout.LayoutParams(RouteOsUi.dp(this, 48), RouteOsUi.dp(this, 54)));
    root.addView(top);

    LinearLayout tabs = new LinearLayout(this);
    tabs.addView(tab("Saved Routes", true), RouteOsUi.params(0, RouteOsUi.dp(this, 44), 1, this));
    tabs.addView(tab("Draw on Map", false), RouteOsUi.params(0, RouteOsUi.dp(this, 44), 1, this));
    tabs.addView(tab("Record Live", false), RouteOsUi.params(0, RouteOsUi.dp(this, 44), 1, this));
    root.addView(tabs);

    search = new EditText(this);
    search.setSingleLine(true); search.setHint("⌕   Search saved routes…"); search.setHintTextColor(RouteOsUi.MUTED);
    search.setTextColor(Color.WHITE); search.setTextSize(14); search.setPadding(RouteOsUi.dp(this, 16), 0, RouteOsUi.dp(this, 16), 0);
    search.setBackground(RouteOsUi.background(RouteOsUi.CARD, RouteOsUi.dp(this, 18), RouteOsUi.STROKE));
    LinearLayout.LayoutParams searchParams = new LinearLayout.LayoutParams(-1, RouteOsUi.dp(this, 52)); searchParams.setMargins(0, RouteOsUi.dp(this, 10), 0, RouteOsUi.dp(this, 8)); root.addView(search, searchParams);
    search.addTextChangedListener(new android.text.TextWatcher() {
      public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
      public void onTextChanged(CharSequence s, int start, int before, int count) { renderRoutes(s.toString()); }
      public void afterTextChanged(android.text.Editable s) {}
    });

    filters = new LinearLayout(this); renderFilters();
    root.addView(filters, new LinearLayout.LayoutParams(-1, RouteOsUi.dp(this, 48)));
    ScrollView scroll = new ScrollView(this); routeList = new LinearLayout(this); routeList.setOrientation(LinearLayout.VERTICAL); scroll.addView(routeList);
    root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));

    TextView continueButton = RouteOsUi.text(this, "Continue  ›", 17, Color.rgb(4, 35, 27), true); continueButton.setGravity(Gravity.CENTER);
    continueButton.setBackground(RouteOsUi.background(RouteOsUi.GREEN, RouteOsUi.dp(this, 28), Color.TRANSPARENT));
    RouteOsUi.pressable(continueButton, this::continueWithSelection);
    LinearLayout.LayoutParams buttonParams = new LinearLayout.LayoutParams(-1, RouteOsUi.dp(this, 58)); buttonParams.setMargins(0, RouteOsUi.dp(this, 10), 0, 0); root.addView(continueButton, buttonParams);
    setContentView(root);
    String initialQuery = getIntent().getStringExtra("routeos_query");
    if (initialQuery != null) search.setText(initialQuery);
    routeList.addView(RouteOsUi.text(this, "Loading saved routes…", 14, RouteOsUi.MUTED, false));
    loadRoutes();
  }

  private View tab(String label, boolean active) {
    TextView view = RouteOsUi.text(this, label, 12, active ? Color.WHITE : RouteOsUi.MUTED, active); view.setGravity(Gravity.CENTER);
    view.setBackground(RouteOsUi.background(active ? Color.rgb(0, 112, 79) : Color.rgb(18, 27, 37), RouteOsUi.dp(this, 14), active ? RouteOsUi.GREEN : Color.TRANSPARENT));
    if (label.startsWith("Draw")) RouteOsUi.pressable(view, this::startDrawing);
    if (label.startsWith("Record")) RouteOsUi.pressable(view, this::startRecording);
    return view;
  }

  private View chip(String label, boolean active) {
    TextView chip = RouteOsUi.text(this, label, 12, active ? Color.WHITE : RouteOsUi.MUTED, active); chip.setGravity(Gravity.CENTER);
    chip.setBackground(RouteOsUi.background(active ? Color.rgb(0, 125, 83) : Color.TRANSPARENT, RouteOsUi.dp(this, 18), active ? RouteOsUi.GREEN : RouteOsUi.STROKE));
    RouteOsUi.pressable(chip, () -> { routeFilter = label; selected = -1; renderFilters(); renderRoutes(search.getText().toString()); });
    LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-2, RouteOsUi.dp(this, 38)); params.setMargins(0, 4, RouteOsUi.dp(this, 8), 4); chip.setLayoutParams(params); chip.setPadding(RouteOsUi.dp(this, 17), 0, RouteOsUi.dp(this, 17), 0); return chip;
  }

  private void renderFilters() {
    filters.removeAllViews(); filters.addView(chip("All", routeFilter.equals("All")));
    filters.addView(chip("My Routes", routeFilter.equals("My Routes")));
    filters.addView(chip("Assigned", routeFilter.equals("Assigned")));
    filters.addView(chip("Nearby", routeFilter.equals("Nearby")));
    filters.addView(chip("Favourites", routeFilter.equals("Favourites")));
    filters.addView(chip("Recent", routeFilter.equals("Recent")));
  }

  private void loadRoutes() {
    executor.execute(() -> {
      try { JSONArray data = RouteOsApi.getRoutes(this); routes.clear(); for (int i = 0; i < data.length(); i++) routes.add(data.getJSONObject(i)); runOnUiThread(() -> renderRoutes(search.getText().toString())); }
      catch (Exception error) { runOnUiThread(() -> { routeList.removeAllViews(); routeList.addView(RouteOsUi.text(this, "RouteOS backend unavailable", 14, Color.rgb(255, 104, 116), false)); }); }
    });
  }

  private void renderRoutes(String query) {
    if (routeList == null) return; routeList.removeAllViews(); String filter = query.trim().toLowerCase(java.util.Locale.ROOT);
    long driverId = getSharedPreferences("routeos", MODE_PRIVATE).getLong("driver_id", 0);
    java.util.List<Integer> nearby = null;
    if (routeFilter.equals("Nearby")) {
      nearby = new java.util.ArrayList<>();
      for (int i = 0; i < routes.size(); i++) if (distanceToHub(routes.get(i)) >= 0) nearby.add(i);
      nearby.sort(java.util.Comparator.comparingDouble(i -> distanceToHub(routes.get(i))));
      if (nearby.size() > 5) nearby = new java.util.ArrayList<>(nearby.subList(0, 5));
    }
    for (int index = 0; index < routes.size(); index++) {
      JSONObject route = routes.get(index);
      String searchable = route.optString("name") + " " + route.optString("origin") + " " + route.optString("destination") + " " + route.optString("recorder_name");
      if (!searchable.toLowerCase(java.util.Locale.ROOT).contains(filter)) continue;
      boolean mine = route.optLong("recorder_id") == driverId;
      if (routeFilter.equals("My Routes") && !mine) continue;
      if (routeFilter.equals("Assigned") && mine) continue;
      if (routeFilter.equals("Nearby") && (nearby == null || !nearby.contains(index))) continue;
      if (routeFilter.equals("Favourites") && !route.optBoolean("is_favorite")) continue;
      if (routeFilter.equals("Recent") && route.isNull("last_used_at")) continue;
      final int routeIndex = index; boolean active = selected == index;
      LinearLayout card = new LinearLayout(this); card.setGravity(Gravity.CENTER_VERTICAL); card.setPadding(RouteOsUi.dp(this, 10), RouteOsUi.dp(this, 8), RouteOsUi.dp(this, 10), RouteOsUi.dp(this, 8));
      card.setBackground(RouteOsUi.background(active ? Color.rgb(18, 48, 40) : RouteOsUi.CARD, RouteOsUi.dp(this, 16), active ? RouteOsUi.GREEN : Color.TRANSPARENT));
      TextView mapTile = RouteOsUi.text(this, "⌁", 28, active ? RouteOsUi.GREEN : Color.rgb(99, 186, 238), true); mapTile.setGravity(Gravity.CENTER); mapTile.setBackground(RouteOsUi.background(Color.rgb(22, 69, 60), RouteOsUi.dp(this, 12), Color.TRANSPARENT)); card.addView(mapTile, new LinearLayout.LayoutParams(RouteOsUi.dp(this, 64), RouteOsUi.dp(this, 64)));
      LinearLayout copy = new LinearLayout(this); copy.setOrientation(LinearLayout.VERTICAL); copy.setPadding(RouteOsUi.dp(this, 12), 0, 0, 0);
      copy.addView(RouteOsUi.text(this, route.optString("name", "Saved route"), 15, Color.WHITE, true));
      copy.addView(RouteOsUi.text(this, route.optString("origin", "Recorded") + "  →  " + route.optString("destination", "Route"), 12, RouteOsUi.MUTED, false));
      copy.addView(RouteOsUi.text(this, "Saved " + relativeDate(route.optString("created_at")) + "  •  " + route.optString("recorder_name", "RouteOS"), 11, RouteOsUi.MUTED, false));
      card.addView(copy, new LinearLayout.LayoutParams(0, RouteOsUi.dp(this, 68), 1));
      TextView actions = RouteOsUi.text(this, "⋯", 24, RouteOsUi.MUTED, true); actions.setGravity(Gravity.CENTER);
      RouteOsUi.pressable(actions, () -> showRouteDetails(routeIndex));
      card.addView(actions, new LinearLayout.LayoutParams(RouteOsUi.dp(this, 36), -1));
      TextView radio = RouteOsUi.text(this, active ? "●" : "○", 25, active ? RouteOsUi.GREEN : RouteOsUi.MUTED, true); radio.setGravity(Gravity.CENTER); card.addView(radio, new LinearLayout.LayoutParams(RouteOsUi.dp(this, 34), -1));
      RouteOsUi.pressable(card, () -> { selected = routeIndex; renderRoutes(search.getText().toString()); });
      LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, RouteOsUi.dp(this, 84)); params.setMargins(0, 0, 0, RouteOsUi.dp(this, 8)); routeList.addView(card, params);
    }
    if (routeList.getChildCount() == 0) routeList.addView(RouteOsUi.text(this,
        routes.isEmpty() ? "No saved routes yet. Record or draw one from Home." : "No matching saved routes", 14, RouteOsUi.MUTED, false));
  }

  private void showRouteDetails(int index) {
    if (index < 0 || index >= routes.size()) return;
    JSONObject route = routes.get(index);
    String type = "drawn".equals(route.optString("route_type")) ? "Drawn route" : "Recorded track";
    double km = route.optDouble("distance_meters", 0) / 1000.0;
    long seconds = route.optLong("duration_seconds", 0);
    String duration = seconds > 0 ? (seconds / 60) + " min" : "—";
    String message = route.optString("origin", "Current hub") + " → " + route.optString("destination", "Destination")
        + "\n\n" + String.format(java.util.Locale.ROOT, "%.1f km  •  %s", km, duration)
        + "\n" + type + "  •  " + route.optInt("point_count", 0) + " GPS points"
        + "\nRecorded by " + route.optString("recorder_name", "RouteOS");
    android.app.AlertDialog dialog = new android.app.AlertDialog.Builder(this)
        .setTitle(route.optString("name", "Saved route"))
        .setMessage(message)
        .setPositiveButton("Use route", (d, which) -> { selected = index; markRecentAndImport(route); })
        .setNeutralButton(route.optBoolean("is_favorite") ? "Unfavourite" : "Favourite", (d, which) -> toggleFavorite(route))
        .setNegativeButton("More", null).create();
    dialog.setOnShowListener(ignored -> {
      dialog.getButton(android.app.AlertDialog.BUTTON_NEGATIVE).setOnClickListener(v -> showRouteActions(dialog, index));
    });
    dialog.show();
  }

  private void showRouteActions(android.app.AlertDialog details, int index) {
    details.dismiss();
    if (index < 0 || index >= routes.size()) return;
    JSONObject route = routes.get(index);
    String[] actions = {"Show on map", "Rename", "Share with drivers", "Clear from recent", "Delete route"};
    new android.app.AlertDialog.Builder(this).setTitle("Route actions")
        .setItems(actions, (d, which) -> {
          if (which == 0) previewRoute(route);
          else if (which == 1) renameRoute(index);
          else if (which == 2) shareRoute(index);
          else if (which == 3) clearRecent(route);
          else confirmDelete(index);
        }).show();
  }

  private boolean canManage(JSONObject route) {
    long id = getSharedPreferences("routeos", MODE_PRIVATE).getLong("driver_id", 0);
    String role = getSharedPreferences("routeos", MODE_PRIVATE).getString("role", "driver");
    return "admin".equals(role) || route.optLong("recorder_id") == id;
  }

  private void renameRoute(int index) {
    JSONObject route = routes.get(index);
    if (!canManage(route)) { toast("Only the route owner or admin can rename this route"); return; }
    EditText input = new EditText(this); input.setSingleLine(true); input.setText(route.optString("name")); input.setSelectAllOnFocus(true);
    new android.app.AlertDialog.Builder(this).setTitle("Rename route").setView(input)
        .setNegativeButton("Cancel", null).setPositiveButton("Save", (d, w) -> {
          String name = input.getText().toString().trim(); if (name.isEmpty()) { toast("Enter a route name"); return; }
          executor.execute(() -> { try { RouteOsApi.renameRoute(this, route.getLong("id"), name); runOnUiThread(this::loadRoutes); } catch (Exception e) { runOnUiThread(() -> toast("Could not rename route: " + e.getMessage())); } });
        }).show();
  }

  private void toggleFavorite(JSONObject route) {
    executor.execute(() -> { try { RouteOsApi.setFavorite(this, route.getLong("id"), !route.optBoolean("is_favorite")); runOnUiThread(this::loadRoutes); } catch (Exception e) { runOnUiThread(() -> toast("Could not update favourite")); } });
  }

  private void shareRoute(int index) {
    JSONObject route = routes.get(index);
    EditText recipient = new EditText(this); recipient.setSingleLine(true); recipient.setHint("Driver ID (blank = all drivers)"); recipient.setInputType(android.text.InputType.TYPE_CLASS_NUMBER);
    new android.app.AlertDialog.Builder(this).setTitle("Share route").setMessage("Choose a RouteOS driver or share it with all drivers.").setView(recipient)
        .setNegativeButton("Cancel", null).setPositiveButton("Share", (d, w) -> {
          long recipientId = 0; try { if (!recipient.getText().toString().trim().isEmpty()) recipientId = Long.parseLong(recipient.getText().toString().trim()); } catch (NumberFormatException e) { toast("Enter a valid driver ID"); return; }
          final long target = recipientId;
          executor.execute(() -> { try {
            RouteOsApi.shareRoute(this, route.getLong("id"), target);
            runOnUiThread(() -> { Intent send = new Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT, "RouteOS route: " + route.optString("name")); startActivity(Intent.createChooser(send, "Share route")); });
          } catch (Exception e) { runOnUiThread(() -> toast("Could not share route: " + e.getMessage())); } });
        }).show();
  }

  private void clearRecent(JSONObject route) {
    executor.execute(() -> { try { RouteOsApi.clearRecent(this, route.getLong("id")); runOnUiThread(this::loadRoutes); } catch (Exception e) { runOnUiThread(() -> toast("Could not clear recent route")); } });
  }

  private void confirmDelete(int index) {
    JSONObject route = routes.get(index);
    if (!canManage(route)) { toast("Only the route owner or admin can delete this route"); return; }
    new android.app.AlertDialog.Builder(this).setTitle("Delete route?")
        .setMessage("Delete ‘" + route.optString("name", "Saved route") + "’? This cannot be undone.")
        .setNegativeButton("Cancel", null).setPositiveButton("Delete", (d, w) -> executor.execute(() -> {
          try { RouteOsApi.deleteRoute(this, route.getLong("id")); if (selected == index) selected = -1; runOnUiThread(this::loadRoutes); }
          catch (Exception e) { runOnUiThread(() -> toast("Route was not deleted: " + e.getMessage())); }
        })).show();
  }

  private void markRecentAndImport(JSONObject route) {
    executor.execute(() -> { try { RouteOsApi.markRecent(this, route.getLong("id")); } catch (Exception ignored) {} });
    importRoute(route);
  }

  private void previewRoute(JSONObject route) {
    loadRouteFile(route, false);
  }

  private void toast(String message) { Toast.makeText(this, message, Toast.LENGTH_LONG).show(); }

  /** Metres from the current GPS position to the route's hub, or -1 when unknown. */
  private double distanceToHub(JSONObject route) {
    if (route.isNull("hub_latitude") || route.isNull("hub_longitude")) return -1;
    android.location.Location here = MwmApplication.from(this).getLocationHelper().getSavedLocation();
    if (here == null) return -1;
    float[] results = new float[1];
    android.location.Location.distanceBetween(here.getLatitude(), here.getLongitude(),
                                              route.optDouble("hub_latitude"), route.optDouble("hub_longitude"), results);
    return results[0];
  }

  private static String relativeDate(String iso) {
    if (iso == null || iso.isEmpty()) return "recently";
    try {
      long then = java.time.Instant.parse(iso).toEpochMilli();
      long diff = System.currentTimeMillis() - then;
      java.util.concurrent.TimeUnit unit = java.util.concurrent.TimeUnit.MILLISECONDS;
      if (unit.toDays(diff) < 1) return "today";
      long days = unit.toDays(diff);
      if (days == 1) return "yesterday";
      if (days < 30) return days + " days ago";
      if (days < 60) return "last month";
      return (days / 30) + " months ago";
    } catch (Exception ignored) { return "recently"; }
  }

  private void continueWithSelection() {
    if (selected < 0 || selected >= routes.size()) { Toast.makeText(this, "Select a route first", Toast.LENGTH_SHORT).show(); return; }
    markRecentAndImport(routes.get(selected));
  }

  private void importRoute(JSONObject summary) {
    loadRouteFile(summary, true);
  }

  private void loadRouteFile(JSONObject summary, boolean openVehicle) {
    executor.execute(() -> {
      try {
        JSONObject route = requestObject("/api/v1/routes/" + summary.getLong("id")); JSONArray points = route.getJSONArray("points");
        if (points.length() < 2) throw new IllegalArgumentException("route has no usable track"); JSONArray coordinates = new JSONArray();
        for (int i = 0; i < points.length(); i++) { JSONObject point = points.getJSONObject(i); coordinates.put(new JSONArray().put(point.getDouble("longitude")).put(point.getDouble("latitude"))); }
        JSONObject feature = new JSONObject().put("type", "Feature").put("geometry", new JSONObject().put("type", "LineString").put("coordinates", coordinates)).put("properties", new JSONObject().put("name", route.optString("name", "RouteOS route")));
        File file = new File(getCacheDir(), "routeos-route-" + route.getLong("id") + ".geojson");
        try (FileOutputStream output = new FileOutputStream(file)) { output.write(new JSONObject().put("type", "FeatureCollection").put("features", new JSONArray().put(feature)).toString().getBytes(StandardCharsets.UTF_8)); }
        JSONObject destination = points.getJSONObject(points.length() - 1);
        runOnUiThread(() -> {
          BookmarkManager.INSTANCE.loadBookmarksFile(file.getAbsolutePath(), true);
          if (!openVehicle) {
            startActivity(new Intent(this, MwmActivity.class).putExtra("routeos_map", true).putExtra("routeos_skip_home", true)); finish(); return;
          }
          Intent vehicle = new android.content.Intent(this, RouteOsVehicleActivity.class)
              .putExtra("route_id", route.optLong("id"))
              .putExtra("route_name", route.optString("name", "RouteOS route"))
              .putExtra("destination_lat", destination.optDouble("latitude"))
              .putExtra("destination_lon", destination.optDouble("longitude"));
          startActivity(vehicle); finish();
        });
      } catch (Exception error) { runOnUiThread(() -> Toast.makeText(this, "Could not load route: " + error.getMessage(), Toast.LENGTH_LONG).show()); }
    });
  }

  private JSONObject requestObject(String path) throws Exception {
    HttpURLConnection connection = (HttpURLConnection) new URL(API + path).openConnection(); connection.setConnectTimeout(3000); connection.setReadTimeout(5000);
    if (connection.getResponseCode() != 200) throw new IllegalStateException("HTTP " + connection.getResponseCode());
    return new JSONObject(RouteOsApi.readFully(connection.getInputStream()));
  }

  private void openNativeMap() { startActivity(new android.content.Intent(this, MwmActivity.class).putExtra("routeos_home", true)); finish(); }
  private void openNativeMap(String routeName) { startActivity(new android.content.Intent(this, MwmActivity.class).putExtra("routeos_route_name", routeName)); finish(); }
  private void startRecording() { startActivity(new android.content.Intent(this, MwmActivity.class).putExtra("routeos_start_recording", true).putExtra("routeos_skip_home", true)); finish(); }
  private void startDrawing() { startActivity(new android.content.Intent(this, MwmActivity.class).putExtra("routeos_draw_route", true).putExtra("routeos_skip_home", true)); finish(); }
  @Override protected void onDestroy() { executor.shutdownNow(); super.onDestroy(); }

  @Override protected void onResume() { super.onResume(); if (routeList != null) loadRoutes(); }
}
