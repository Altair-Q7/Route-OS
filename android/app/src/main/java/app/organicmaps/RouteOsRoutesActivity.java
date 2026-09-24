package app.organicmaps;

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
    filters.addView(chip("Recent", routeFilter.equals("Recent")));
  }

  private void loadRoutes() {
    executor.execute(() -> {
      try { JSONArray data = RouteOsApi.getRoutes(); routes.clear(); for (int i = 0; i < data.length(); i++) routes.add(data.getJSONObject(i)); runOnUiThread(() -> renderRoutes(search.getText().toString())); }
      catch (Exception error) { runOnUiThread(() -> { routeList.removeAllViews(); routeList.addView(RouteOsUi.text(this, "RouteOS backend unavailable", 14, Color.rgb(255, 104, 116), false)); }); }
    });
  }

  private void renderRoutes(String query) {
    if (routeList == null) return; routeList.removeAllViews(); String filter = query.trim().toLowerCase(java.util.Locale.ROOT);
    for (int index = 0; index < routes.size(); index++) {
      JSONObject route = routes.get(index);
      String searchable = route.optString("name") + " " + route.optString("origin") + " " + route.optString("destination") + " " + route.optString("recorder_name");
      if (!searchable.toLowerCase(java.util.Locale.ROOT).contains(filter)) continue;
      if (routeFilter.equals("My Routes") && route.optLong("recorder_id") != getSharedPreferences("routeos", MODE_PRIVATE).getLong("driver_id", 0)) continue;
      if (routeFilter.equals("Recent") && index >= 5) continue;
      final int routeIndex = index; boolean active = selected == index;
      LinearLayout card = new LinearLayout(this); card.setGravity(Gravity.CENTER_VERTICAL); card.setPadding(RouteOsUi.dp(this, 10), RouteOsUi.dp(this, 8), RouteOsUi.dp(this, 10), RouteOsUi.dp(this, 8));
      card.setBackground(RouteOsUi.background(active ? Color.rgb(18, 48, 40) : RouteOsUi.CARD, RouteOsUi.dp(this, 16), active ? RouteOsUi.GREEN : Color.TRANSPARENT));
      TextView mapTile = RouteOsUi.text(this, "⌁", 28, active ? RouteOsUi.GREEN : Color.rgb(99, 186, 238), true); mapTile.setGravity(Gravity.CENTER); mapTile.setBackground(RouteOsUi.background(Color.rgb(22, 69, 60), RouteOsUi.dp(this, 12), Color.TRANSPARENT)); card.addView(mapTile, new LinearLayout.LayoutParams(RouteOsUi.dp(this, 64), RouteOsUi.dp(this, 64)));
      LinearLayout copy = new LinearLayout(this); copy.setOrientation(LinearLayout.VERTICAL); copy.setPadding(RouteOsUi.dp(this, 12), 0, 0, 0);
      copy.addView(RouteOsUi.text(this, route.optString("name", "Saved route"), 15, Color.WHITE, true));
      copy.addView(RouteOsUi.text(this, route.optString("origin", "Recorded") + "  →  " + route.optString("destination", "Route"), 12, RouteOsUi.MUTED, false));
      copy.addView(RouteOsUi.text(this, "Shared RouteOS track", 11, RouteOsUi.MUTED, false));
      card.addView(copy, new LinearLayout.LayoutParams(0, RouteOsUi.dp(this, 68), 1));
      TextView radio = RouteOsUi.text(this, active ? "●" : "○", 25, active ? RouteOsUi.GREEN : RouteOsUi.MUTED, true); radio.setGravity(Gravity.CENTER); card.addView(radio, new LinearLayout.LayoutParams(RouteOsUi.dp(this, 42), -1));
      RouteOsUi.pressable(card, () -> { selected = routeIndex; renderRoutes(search.getText().toString()); });
      LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, RouteOsUi.dp(this, 84)); params.setMargins(0, 0, 0, RouteOsUi.dp(this, 8)); routeList.addView(card, params);
    }
    if (routeList.getChildCount() == 0) routeList.addView(RouteOsUi.text(this, "No matching saved routes", 14, RouteOsUi.MUTED, false));
  }

  private void continueWithSelection() {
    if (selected < 0 || selected >= routes.size()) { Toast.makeText(this, "Select a route first", Toast.LENGTH_SHORT).show(); return; }
    importRoute(routes.get(selected));
  }

  private void importRoute(JSONObject summary) {
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
    return new JSONObject(new String(connection.getInputStream().readAllBytes(), StandardCharsets.UTF_8));
  }

  private void openNativeMap() { startActivity(new android.content.Intent(this, MwmActivity.class).putExtra("routeos_skip_home", true)); finish(); }
  private void openNativeMap(String routeName) { startActivity(new android.content.Intent(this, MwmActivity.class).putExtra("routeos_skip_home", true).putExtra("routeos_route_name", routeName)); finish(); }
  private void startRecording() { startActivity(new android.content.Intent(this, MwmActivity.class).putExtra("routeos_start_recording", true).putExtra("routeos_skip_home", true)); finish(); }
  private void startDrawing() { startActivity(new android.content.Intent(this, MwmActivity.class).putExtra("routeos_draw_route", true).putExtra("routeos_skip_home", true)); finish(); }
  @Override protected void onDestroy() { executor.shutdownNow(); super.onDestroy(); }
}
