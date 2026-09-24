package app.organicmaps;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import androidx.annotation.Nullable;
import com.google.android.material.dialog.MaterialAlertDialogBuilder;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.json.JSONArray;
import org.json.JSONObject;

/** RouteOS' translucent command surface over the native Organic Maps map. */
public final class RouteOsHomeActivity extends Activity {
  private final ExecutorService executor = Executors.newSingleThreadExecutor();
  private LinearLayout recentRoutes;
  private LinearLayout activeRidePanel;
  private TextView profile;

  @Override public void onCreate(@Nullable Bundle state) {
    super.onCreate(state);
    long accountId = getSharedPreferences("routeos", MODE_PRIVATE).getLong("driver_id", 0);
    if (accountId == 0) {
      startActivity(new Intent(this, RouteOsLoginActivity.class)); finish(); return;
    }
    if ("admin".equals(getSharedPreferences("routeos", MODE_PRIVATE).getString("role", "driver"))) {
      startActivity(new Intent(this, MwmActivity.class).putExtra("routeos_admin", true).putExtra("routeos_skip_home", true)); finish(); return;
    }
    getWindow().setStatusBarColor(Color.TRANSPARENT);
    getWindow().setNavigationBarColor(RouteOsUi.BG);

    FrameLayout root = new FrameLayout(this);
    LinearLayout content = new LinearLayout(this);
    content.setOrientation(LinearLayout.VERTICAL);
    content.setPadding(RouteOsUi.dp(this, 16), RouteOsUi.dp(this, 28), RouteOsUi.dp(this, 16), RouteOsUi.dp(this, 12));
    root.addView(content, new FrameLayout.LayoutParams(-1, -1));

    LinearLayout header = new LinearLayout(this);
    header.setGravity(Gravity.CENTER_VERTICAL);
    header.setPadding(RouteOsUi.dp(this, 8), 0, RouteOsUi.dp(this, 8), 0);
    header.setBackground(RouteOsUi.background(Color.argb(245, 8, 15, 22), RouteOsUi.dp(this, 18), Color.TRANSPARENT));
    TextView mark = RouteOsUi.text(this, "◉", 36, RouteOsUi.GREEN, true);
    header.addView(mark, new LinearLayout.LayoutParams(RouteOsUi.dp(this, 54), RouteOsUi.dp(this, 58)));
    LinearLayout titles = new LinearLayout(this);
    titles.setOrientation(LinearLayout.VERTICAL);
    titles.addView(RouteOsUi.text(this, "RouteOS", 24, Color.WHITE, true));
    titles.addView(RouteOsUi.text(this, "Drive. Track. Deliver.", 13, RouteOsUi.MUTED, false));
    header.addView(titles, new LinearLayout.LayoutParams(0, RouteOsUi.dp(this, 60), 1));
    profile = RouteOsUi.text(this, accountInitial(), 18, Color.WHITE, true);
    profile.setGravity(Gravity.CENTER);
    profile.setBackground(RouteOsUi.background(Color.argb(220, 48, 61, 76), 100, RouteOsUi.STROKE));
    RouteOsUi.pressable(profile, this::showLogin);
    header.addView(profile, new LinearLayout.LayoutParams(RouteOsUi.dp(this, 44), RouteOsUi.dp(this, 44)));
    content.addView(header);

    EditText search = new EditText(this);
    search.setSingleLine(true);
    search.setHint("⌕   Search places or routes…");
    search.setHintTextColor(RouteOsUi.MUTED);
    search.setTextColor(Color.WHITE);
    search.setTextSize(14);
    search.setPadding(RouteOsUi.dp(this, 18), 0, RouteOsUi.dp(this, 18), 0);
    search.setBackground(RouteOsUi.background(Color.argb(240, 24, 33, 44), RouteOsUi.dp(this, 28), RouteOsUi.STROKE));
    LinearLayout.LayoutParams searchParams = new LinearLayout.LayoutParams(-1, RouteOsUi.dp(this, 54));
    searchParams.setMargins(0, RouteOsUi.dp(this, 8), 0, RouteOsUi.dp(this, 10));
    content.addView(search, searchParams);
    search.setOnEditorActionListener((view, actionId, event) -> {
      startActivity(new Intent(this, RouteOsSearchActivity.class).putExtra("routeos_query", view.getText().toString())); return true;
    });

    LinearLayout actions = new LinearLayout(this);
    actions.setPadding(RouteOsUi.dp(this, 4), RouteOsUi.dp(this, 4), RouteOsUi.dp(this, 4), RouteOsUi.dp(this, 4));
    actions.setBackground(RouteOsUi.background(RouteOsUi.PANEL, RouteOsUi.dp(this, 22), RouteOsUi.STROKE));
    actions.addView(action("⌁", "Drive a Route", "Follow a saved route", () -> startActivity(new Intent(this, RouteOsRoutesActivity.class))), RouteOsUi.params(0, RouteOsUi.dp(this, 104), 1, this));
    actions.addView(action("●", "Record Route", "Capture a new route", this::startRecording), RouteOsUi.params(0, RouteOsUi.dp(this, 104), 1, this));
    actions.addView(action("＋", "Draw Route", "Hub to a map point", this::startDrawing), RouteOsUi.params(0, RouteOsUi.dp(this, 104), 1, this));
    content.addView(actions);

    activeRidePanel = new LinearLayout(this); activeRidePanel.setGravity(Gravity.CENTER_VERTICAL);
    activeRidePanel.setPadding(RouteOsUi.dp(this, 14), RouteOsUi.dp(this, 8), RouteOsUi.dp(this, 10), RouteOsUi.dp(this, 8));
    activeRidePanel.setBackground(RouteOsUi.background(Color.rgb(8, 82, 61), RouteOsUi.dp(this, 18), RouteOsUi.GREEN));
    activeRidePanel.setVisibility(View.GONE);
    LinearLayout.LayoutParams activeParams = new LinearLayout.LayoutParams(-1, RouteOsUi.dp(this, 68)); activeParams.setMargins(0, RouteOsUi.dp(this, 8), 0, 0); content.addView(activeRidePanel, activeParams);

    LinearLayout recentPanel = new LinearLayout(this);
    recentPanel.setOrientation(LinearLayout.VERTICAL);
    recentPanel.setPadding(RouteOsUi.dp(this, 12), RouteOsUi.dp(this, 10), RouteOsUi.dp(this, 12), RouteOsUi.dp(this, 12));
    recentPanel.setBackground(RouteOsUi.background(RouteOsUi.PANEL, RouteOsUi.dp(this, 22), RouteOsUi.STROKE));
    LinearLayout.LayoutParams panelParams = new LinearLayout.LayoutParams(-1, RouteOsUi.dp(this, 300));
    panelParams.setMargins(0, RouteOsUi.dp(this, 10), 0, RouteOsUi.dp(this, 10));
    content.addView(recentPanel, panelParams);

    LinearLayout recentTitle = new LinearLayout(this);
    TextView title = RouteOsUi.text(this, "Recent Routes", 17, Color.WHITE, true);
    recentTitle.addView(title, new LinearLayout.LayoutParams(0, RouteOsUi.dp(this, 38), 1));
    TextView seeAll = RouteOsUi.text(this, "See all", 14, RouteOsUi.GREEN, true);
    RouteOsUi.pressable(seeAll, () -> startActivity(new Intent(this, RouteOsRoutesActivity.class)));
    recentTitle.addView(seeAll, new LinearLayout.LayoutParams(RouteOsUi.dp(this, 70), RouteOsUi.dp(this, 38)));
    recentPanel.addView(recentTitle);
    ScrollView scroll = new ScrollView(this);
    recentRoutes = new LinearLayout(this);
    recentRoutes.setOrientation(LinearLayout.VERTICAL);
    scroll.addView(recentRoutes);
    recentPanel.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
    showLoading();

    content.addView(new View(this), new LinearLayout.LayoutParams(-1, 0, 1));

    LinearLayout nav = new LinearLayout(this);
    nav.setGravity(Gravity.CENTER);
    nav.setPadding(RouteOsUi.dp(this, 6), RouteOsUi.dp(this, 4), RouteOsUi.dp(this, 6), RouteOsUi.dp(this, 4));
    nav.setBackground(RouteOsUi.background(Color.argb(248, 8, 15, 22), RouteOsUi.dp(this, 22), RouteOsUi.STROKE));
    nav.addView(navItem("⌂\nHome", true, () -> {}), RouteOsUi.params(0, RouteOsUi.dp(this, 64), 1, this));
    nav.addView(navItem("⌁\nRoutes", false, () -> startActivity(new Intent(this, RouteOsRoutesActivity.class))), RouteOsUi.params(0, RouteOsUi.dp(this, 64), 1, this));
    nav.addView(navItem("⌖\nMap", false, this::openMap), RouteOsUi.params(0, RouteOsUi.dp(this, 64), 1, this));
    content.addView(nav);
    setContentView(root);
    loadRoutes();
    loadActiveRide();
  }

  private View action(String icon, String title, String subtitle, Runnable action) {
    LinearLayout card = new LinearLayout(this);
    card.setOrientation(LinearLayout.VERTICAL);
    card.setGravity(Gravity.CENTER);
    card.setPadding(3, 5, 3, 5);
    card.setBackground(RouteOsUi.background(RouteOsUi.CARD, RouteOsUi.dp(this, 16), Color.TRANSPARENT));
    int color = title.startsWith("Record") ? Color.rgb(255, 83, 99) : RouteOsUi.GREEN;
    card.addView(RouteOsUi.text(this, icon, 25, color, true), new LinearLayout.LayoutParams(-1, RouteOsUi.dp(this, 34)));
    TextView heading = RouteOsUi.text(this, title, 13, Color.WHITE, true); heading.setGravity(Gravity.CENTER); card.addView(heading);
    TextView sub = RouteOsUi.text(this, subtitle, 10, RouteOsUi.MUTED, false); sub.setGravity(Gravity.CENTER); card.addView(sub);
    RouteOsUi.pressable(card, action);
    return card;
  }

  private View navItem(String label, boolean selected, Runnable action) {
    TextView item = RouteOsUi.text(this, label, 12, selected ? RouteOsUi.GREEN : RouteOsUi.MUTED, selected);
    item.setGravity(Gravity.CENTER);
    if (selected) item.setBackground(RouteOsUi.background(Color.argb(80, 0, 120, 91), RouteOsUi.dp(this, 14), Color.TRANSPARENT));
    RouteOsUi.pressable(item, action);
    return item;
  }

  private void showLoading() {
    TextView loading = RouteOsUi.text(this, "Loading saved routes…", 14, RouteOsUi.MUTED, false);
    loading.setPadding(12, 18, 12, 18);
    recentRoutes.addView(loading);
  }

  private void loadRoutes() {
    executor.execute(() -> {
      try {
        JSONArray routes = RouteOsApi.getRoutes();
        runOnUiThread(() -> renderRoutes(routes));
      } catch (Exception error) {
        runOnUiThread(() -> {
          recentRoutes.removeAllViews();
          recentRoutes.addView(RouteOsUi.text(this, "Backend unavailable", 14, Color.rgb(255, 110, 120), false));
        });
      }
    });
  }

  private void loadActiveRide() {
    executor.execute(() -> {
      try { JSONObject ride = RouteOsApi.getDriverActiveRide(this); runOnUiThread(() -> renderActiveRide(ride)); }
      catch (Exception error) { if (error.getMessage() != null && error.getMessage().contains("404")) RouteOsApi.clearActiveRide(this); }
    });
  }

  private void renderActiveRide(JSONObject ride) {
    activeRidePanel.removeAllViews(); activeRidePanel.setVisibility(View.VISIBLE);
    LinearLayout copy = new LinearLayout(this); copy.setOrientation(LinearLayout.VERTICAL);
    copy.addView(RouteOsUi.text(this, "ACTIVE RIDE", 11, RouteOsUi.GREEN, true));
    copy.addView(RouteOsUi.text(this, ride.optString("route_name") + " • " + ride.optString("vehicle_number"), 14, Color.WHITE, true));
    activeRidePanel.addView(copy, new LinearLayout.LayoutParams(0, -1, 1));
    TextView resume = RouteOsUi.text(this, "Resume  ›", 14, Color.WHITE, true); resume.setGravity(Gravity.CENTER);
    resume.setBackground(RouteOsUi.background(Color.rgb(0, 128, 88), RouteOsUi.dp(this, 18), Color.TRANSPARENT));
    RouteOsUi.pressable(resume, () -> {
      getSharedPreferences("routeos", MODE_PRIVATE).edit().putLong("active_ride_id", ride.optLong("id")).apply();
      Intent map = new Intent(this, MwmActivity.class).putExtra("routeos_start_ride", true).putExtra("routeos_skip_home", true)
          .putExtra("routeos_route_name", ride.optString("route_name")).putExtra("routeos_ride_id", ride.optLong("id"))
          .putExtra("routeos_destination_lat", ride.optDouble("destination_latitude", Double.NaN))
          .putExtra("routeos_destination_lon", ride.optDouble("destination_longitude", Double.NaN));
      startActivity(map); finish();
    });
    activeRidePanel.addView(resume, new LinearLayout.LayoutParams(RouteOsUi.dp(this, 116), RouteOsUi.dp(this, 46)));
  }

  private void renderRoutes(JSONArray routes) {
    recentRoutes.removeAllViews();
    if (routes.length() == 0) {
      recentRoutes.addView(RouteOsUi.text(this, "No routes yet. Record your first route.", 14, RouteOsUi.MUTED, false));
      return;
    }
    for (int index = 0; index < Math.min(3, routes.length()); index++) {
      JSONObject route = routes.optJSONObject(index);
      LinearLayout card = new LinearLayout(this);
      card.setGravity(Gravity.CENTER_VERTICAL);
      card.setPadding(RouteOsUi.dp(this, 12), RouteOsUi.dp(this, 8), RouteOsUi.dp(this, 10), RouteOsUi.dp(this, 8));
      card.setBackground(RouteOsUi.background(RouteOsUi.CARD, RouteOsUi.dp(this, 14), Color.TRANSPARENT));
      TextView routeIcon = RouteOsUi.text(this, "⌁", 24, RouteOsUi.GREEN, true); routeIcon.setGravity(Gravity.CENTER); card.addView(routeIcon, new LinearLayout.LayoutParams(RouteOsUi.dp(this, 42), -1));
      LinearLayout copy = new LinearLayout(this); copy.setOrientation(LinearLayout.VERTICAL);
      copy.addView(RouteOsUi.text(this, route.optString("name", "Saved route"), 15, Color.WHITE, true));
      String endpoints = route.optString("origin", "Hub") + "  →  " + route.optString("destination", "Route")
                         + "  •  " + route.optString("recorder_name", "Driver");
      copy.addView(RouteOsUi.text(this, endpoints, 12, RouteOsUi.MUTED, false));
      card.addView(copy, new LinearLayout.LayoutParams(0, RouteOsUi.dp(this, 54), 1));
      TextView play = RouteOsUi.text(this, "▶", 16, Color.WHITE, true); play.setGravity(Gravity.CENTER); card.addView(play, new LinearLayout.LayoutParams(RouteOsUi.dp(this, 42), RouteOsUi.dp(this, 42)));
      RouteOsUi.pressable(card, () -> startActivity(new Intent(this, RouteOsRoutesActivity.class)
          .putExtra("routeos_query", route.optString("name"))));
      LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, RouteOsUi.dp(this, 66)); params.setMargins(0, 0, 0, RouteOsUi.dp(this, 7)); recentRoutes.addView(card, params);
    }
  }

  private void startRecording() {
    Intent intent = new Intent(this, MwmActivity.class).putExtra("routeos_start_recording", true).putExtra("routeos_skip_home", true);
    startActivity(intent);
    finish();
  }

  private void openMap() {
    Intent intent = new Intent(this, MwmActivity.class).putExtra("routeos_map", true).putExtra("routeos_skip_home", true);
    startActivity(intent);
    finish();
  }

  private void startDrawing() {
    Intent intent = new Intent(this, MwmActivity.class).putExtra("routeos_draw_route", true).putExtra("routeos_skip_home", true);
    startActivity(intent);
    finish();
  }

  private String accountInitial() {
    String name = getSharedPreferences("routeos", MODE_PRIVATE).getString("driver_name", "?");
    return name == null || name.isBlank() ? "?" : name.substring(0, 1).toUpperCase(java.util.Locale.ROOT);
  }

  private void showLogin() {
    new MaterialAlertDialogBuilder(this)
        .setTitle(getSharedPreferences("routeos", MODE_PRIVATE).getString("driver_name", "RouteOS account"))
        .setMessage("Driver account • shared routes are available to all drivers.")
        .setNegativeButton(android.R.string.cancel, null)
        .setPositiveButton("Switch account", (dialog, which) -> {
          RouteOsApi.logout(this); startActivity(new Intent(this, RouteOsLoginActivity.class)); finish();
        }).show();
  }

  @Override protected void onDestroy() {
    executor.shutdownNow();
    super.onDestroy();
  }
}
