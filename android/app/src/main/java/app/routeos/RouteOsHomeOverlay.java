package app.routeos;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import androidx.annotation.NonNull;
import app.organicmaps.sdk.location.LocationState;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * RouteOS map-first home surface.
 *
 * <p>The chrome is a mostly transparent overlay, so the native Organic Maps map underneath stays
 * visible and interactive exactly as it does on the plain map screen. Only the panels themselves
 * are opaque.
 */
public final class RouteOsHomeOverlay
{
  /** Actions that need the map host; everything else is a plain RouteOS screen. */
  public interface Host
  {
    void routeOsStartRecording();

    void routeOsStartDrawing();

    void routeOsShowAccount();

    void routeOsEndRide();

    void routeOsResumeRide(@NonNull JSONObject ride);
  }

  private final Activity mActivity;
  private final Host mHost;
  private final ExecutorService mExecutor = Executors.newSingleThreadExecutor();
  private final Handler mUi = new Handler(Looper.getMainLooper());

  private LinearLayout mRecentRoutes;
  private LinearLayout mActiveRidePanel;
  private TextView mActiveRideDetail;
  private TextView mActiveRidePrimary;
  private FrameLayout mRoot;
  private boolean mDestroyed;

  public RouteOsHomeOverlay(@NonNull Activity activity, @NonNull Host host)
  {
    mActivity = activity;
    mHost = host;
  }

  /** Returns the cached overlay so the map host can detach and re-attach a single view instance. */
  public FrameLayout build()
  {
    if (mRoot != null)
      return mRoot;

    FrameLayout root = new FrameLayout(mActivity);
    mRoot = root;

    LinearLayout content = new LinearLayout(mActivity);
    content.setOrientation(LinearLayout.VERTICAL);
    // Reserve the bottom bar's strip so an overflowing list can never push it off screen.
    content.setPadding(RouteOsUi.dp(mActivity, 16), RouteOsUi.dp(mActivity, 26), RouteOsUi.dp(mActivity, 16),
                       RouteOsUi.dp(mActivity, 88));
    root.addView(content, new FrameLayout.LayoutParams(-1, -1));

    content.addView(buildHeader());
    content.addView(buildSearch());
    content.addView(buildActions());
    content.addView(buildActiveRide());
    content.addView(buildRecentRoutes());

    // Transparent filler: the map shows through between the panels and the bottom navigation.
    content.addView(new View(mActivity), new LinearLayout.LayoutParams(-1, 0, 1));

    root.addView(buildNavigation(), navigationParams());
    root.addView(buildRecenterButton(), recenterParams());

    refresh();
    return root;
  }

  private View buildHeader()
  {
    LinearLayout header = new LinearLayout(mActivity);
    header.setGravity(Gravity.CENTER_VERTICAL);
    header.setPadding(RouteOsUi.dp(mActivity, 12), 0, RouteOsUi.dp(mActivity, 12), 0);
    header.setBackground(RouteOsUi.background(Color.argb(244, 9, 15, 22), RouteOsUi.dp(mActivity, 18),
                                              Color.TRANSPARENT));

    View mark = new View(mActivity);
    mark.setBackground(RouteOsUi.ring());
    header.addView(mark, new LinearLayout.LayoutParams(RouteOsUi.dp(mActivity, 38), RouteOsUi.dp(mActivity, 38)));

    LinearLayout titles = new LinearLayout(mActivity);
    titles.setOrientation(LinearLayout.VERTICAL);
    titles.setPadding(RouteOsUi.dp(mActivity, 12), 0, 0, 0);
    titles.addView(RouteOsUi.text(mActivity, "RouteOS", 21, Color.WHITE, true));
    titles.addView(RouteOsUi.text(mActivity, "Drive. Track. Deliver.", 12, RouteOsUi.MUTED, false));
    header.addView(titles, new LinearLayout.LayoutParams(0, RouteOsUi.dp(mActivity, 50), 1));

    TextView profile = RouteOsUi.text(mActivity, accountInitial(), 16, Color.WHITE, true);
    profile.setGravity(Gravity.CENTER);
    profile.setBackground(RouteOsUi.background(Color.argb(225, 33, 47, 60), 100, RouteOsUi.STROKE));
    RouteOsUi.pressable(profile, () -> mHost.routeOsShowAccount());
    header.addView(profile, new LinearLayout.LayoutParams(RouteOsUi.dp(mActivity, 40), RouteOsUi.dp(mActivity, 40)));

    LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, RouteOsUi.dp(mActivity, 60));
    params.setMargins(0, 0, 0, RouteOsUi.dp(mActivity, 8));
    header.setLayoutParams(params);
    return header;
  }

  private View buildSearch()
  {
    TextView search = RouteOsUi.text(mActivity, "Search places or routes…", 14, RouteOsUi.MUTED, false);
    search.setGravity(Gravity.CENTER_VERTICAL);
    search.setCompoundDrawables(RouteOsUi.glyph(mActivity, "⌕", RouteOsUi.MUTED), null, null, null);
    search.setCompoundDrawablePadding(RouteOsUi.dp(mActivity, 8));
    search.setPadding(RouteOsUi.dp(mActivity, 16), 0, RouteOsUi.dp(mActivity, 16), 0);
    search.setBackground(RouteOsUi.background(RouteOsUi.CARD, RouteOsUi.dp(mActivity, 26), RouteOsUi.STROKE));
    RouteOsUi.pressable(search, () -> mActivity.startActivity(new Intent(mActivity, RouteOsSearchActivity.class)));
    LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, RouteOsUi.dp(mActivity, 50));
    params.setMargins(0, 0, 0, RouteOsUi.dp(mActivity, 8));
    search.setLayoutParams(params);
    return search;
  }

  private View buildActions()
  {
    LinearLayout actions = new LinearLayout(mActivity);
    actions.setPadding(RouteOsUi.dp(mActivity, 4), RouteOsUi.dp(mActivity, 4), RouteOsUi.dp(mActivity, 4),
                       RouteOsUi.dp(mActivity, 4));
    actions.setBackground(RouteOsUi.background(RouteOsUi.PANEL, RouteOsUi.dp(mActivity, 20), RouteOsUi.STROKE));
    actions.addView(action("⌁", "Drive a Route", "Follow a saved route", RouteOsUi.GREEN,
                           () -> mActivity.startActivity(new Intent(mActivity, RouteOsRoutesActivity.class))),
                    RouteOsUi.params(0, RouteOsUi.dp(mActivity, 94), 1, mActivity));
    actions.addView(action("●", "Record Route", "Capture a new route", Color.rgb(255, 83, 99),
                           mHost::routeOsStartRecording),
                    RouteOsUi.params(0, RouteOsUi.dp(mActivity, 94), 1, mActivity));
    actions.addView(action("＋", "Draw Route", "Plan on map", Color.rgb(168, 132, 255), mHost::routeOsStartDrawing),
                    RouteOsUi.params(0, RouteOsUi.dp(mActivity, 94), 1, mActivity));
    return actions;
  }

  private View buildActiveRide()
  {
    mActiveRidePanel = new LinearLayout(mActivity);
    mActiveRidePanel.setGravity(Gravity.CENTER_VERTICAL);
    mActiveRidePanel.setPadding(RouteOsUi.dp(mActivity, 14), RouteOsUi.dp(mActivity, 8), RouteOsUi.dp(mActivity, 10),
                                RouteOsUi.dp(mActivity, 8));
    mActiveRidePanel.setBackground(
        RouteOsUi.background(Color.rgb(8, 74, 56), RouteOsUi.dp(mActivity, 16), RouteOsUi.GREEN));
    mActiveRidePanel.setVisibility(View.GONE);

    LinearLayout copy = new LinearLayout(mActivity);
    copy.setOrientation(LinearLayout.VERTICAL);
    copy.addView(RouteOsUi.text(mActivity, "ACTIVE RIDE", 11, RouteOsUi.GREEN, true));
    mActiveRideDetail = RouteOsUi.text(mActivity, "", 13, Color.WHITE, true);
    copy.addView(mActiveRideDetail);
    mActiveRidePanel.addView(copy, new LinearLayout.LayoutParams(0, -1, 1));

    mActiveRidePrimary = RouteOsUi.text(mActivity, "Resume  ›", 13, Color.WHITE, true);
    mActiveRidePrimary.setGravity(Gravity.CENTER);
    mActiveRidePrimary.setBackground(
        RouteOsUi.background(Color.rgb(0, 128, 88), RouteOsUi.dp(mActivity, 16), Color.TRANSPARENT));
    mActiveRidePanel.addView(mActiveRidePrimary,
                             new LinearLayout.LayoutParams(RouteOsUi.dp(mActivity, 94), RouteOsUi.dp(mActivity, 42)));

    TextView end = RouteOsUi.text(mActivity, "End", 13, Color.WHITE, true);
    end.setGravity(Gravity.CENTER);
    end.setBackground(RouteOsUi.background(Color.rgb(244, 54, 62), RouteOsUi.dp(mActivity, 16), Color.TRANSPARENT));
    end.setPadding(RouteOsUi.dp(mActivity, 12), 0, RouteOsUi.dp(mActivity, 12), 0);
    RouteOsUi.pressable(end, () -> mHost.routeOsEndRide());
    LinearLayout.LayoutParams endParams =
        new LinearLayout.LayoutParams(RouteOsUi.dp(mActivity, 62), RouteOsUi.dp(mActivity, 42));
    endParams.leftMargin = RouteOsUi.dp(mActivity, 8);
    mActiveRidePanel.addView(end, endParams);

    LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, RouteOsUi.dp(mActivity, 64));
    params.setMargins(0, RouteOsUi.dp(mActivity, 8), 0, 0);
    mActiveRidePanel.setLayoutParams(params);
    return mActiveRidePanel;
  }

  private View buildRecentRoutes()
  {
    LinearLayout panel = new LinearLayout(mActivity);
    panel.setOrientation(LinearLayout.VERTICAL);
    panel.setPadding(RouteOsUi.dp(mActivity, 12), RouteOsUi.dp(mActivity, 4), RouteOsUi.dp(mActivity, 12),
                     RouteOsUi.dp(mActivity, 8));
    panel.setBackground(RouteOsUi.background(RouteOsUi.PANEL, RouteOsUi.dp(mActivity, 20), RouteOsUi.STROKE));

    LinearLayout titleRow = new LinearLayout(mActivity);
    titleRow.setGravity(Gravity.CENTER_VERTICAL);
    TextView title = RouteOsUi.text(mActivity, "Recent Routes", 16, Color.WHITE, true);
    titleRow.addView(title, new LinearLayout.LayoutParams(0, RouteOsUi.dp(mActivity, 34), 1));
    TextView seeAll = RouteOsUi.text(mActivity, "See all", 13, RouteOsUi.GREEN, true);
    seeAll.setGravity(Gravity.CENTER_VERTICAL);
    RouteOsUi.pressable(seeAll, () -> mActivity.startActivity(new Intent(mActivity, RouteOsRoutesActivity.class)));
    titleRow.addView(seeAll, new LinearLayout.LayoutParams(RouteOsUi.dp(mActivity, 66), RouteOsUi.dp(mActivity, 34)));
    panel.addView(titleRow);

    mRecentRoutes = new LinearLayout(mActivity);
    mRecentRoutes.setOrientation(LinearLayout.VERTICAL);
    panel.addView(mRecentRoutes, new LinearLayout.LayoutParams(-1, -2));
    showRecentLoading();

    LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, RouteOsUi.dp(mActivity, 232));
    params.setMargins(0, RouteOsUi.dp(mActivity, 8), 0, 0);
    panel.setLayoutParams(params);
    return panel;
  }

  /** Anchored to the bottom of the overlay so it survives any vertical overflow. */
  private LinearLayout buildNavigation()
  {
    LinearLayout nav = new LinearLayout(mActivity);
    nav.setGravity(Gravity.CENTER);
    nav.setPadding(RouteOsUi.dp(mActivity, 6), RouteOsUi.dp(mActivity, 4), RouteOsUi.dp(mActivity, 6),
                   RouteOsUi.dp(mActivity, 4));
    nav.setBackground(RouteOsUi.background(Color.argb(246, 9, 15, 22), RouteOsUi.dp(mActivity, 20), RouteOsUi.STROKE));
    nav.addView(navItem("⌂\nHome", true, this::refresh), RouteOsUi.params(0, RouteOsUi.dp(mActivity, 58), 1, mActivity));
    nav.addView(navItem("⌁\nRoutes", false,
                        () -> mActivity.startActivity(new Intent(mActivity, RouteOsRoutesActivity.class))),
                RouteOsUi.params(0, RouteOsUi.dp(mActivity, 58), 1, mActivity));
    nav.addView(navItem("▰\nVehicles", false, this::openVehiclePicker),
                RouteOsUi.params(0, RouteOsUi.dp(mActivity, 58), 1, mActivity));
    nav.addView(navItem("⋯\nMore", false, mHost::routeOsShowAccount),
                RouteOsUi.params(0, RouteOsUi.dp(mActivity, 58), 1, mActivity));
    LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, RouteOsUi.dp(mActivity, 66));
    params.setMargins(0, RouteOsUi.dp(mActivity, 8), 0, RouteOsUi.dp(mActivity, 14));
    nav.setLayoutParams(params);
    return nav;
  }

  private FrameLayout.LayoutParams navigationParams()
  {
    FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(-1, RouteOsUi.dp(mActivity, 66));
    params.gravity = Gravity.BOTTOM;
    params.leftMargin = RouteOsUi.dp(mActivity, 10);
    params.rightMargin = RouteOsUi.dp(mActivity, 10);
    params.bottomMargin = RouteOsUi.dp(mActivity, 14);
    return params;
  }

  private void openVehiclePicker()
  {
    mActivity.startActivity(
        new Intent(mActivity, RouteOsVehicleActivity.class).putExtra(RouteOsVehicleActivity.EXTRA_SELECT_ONLY, true));
  }

  private View buildRecenterButton()
  {
    TextView button = RouteOsUi.text(mActivity, "◎", 23, Color.WHITE, true);
    button.setGravity(Gravity.CENTER);
    button.setBackground(RouteOsUi.background(Color.argb(238, 24, 34, 45), 100, RouteOsUi.STROKE));
    RouteOsUi.pressable(button, LocationState::nativeSwitchToNextMode);
    return button;
  }

  private FrameLayout.LayoutParams recenterParams()
  {
    FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(RouteOsUi.dp(mActivity, 52),
                                                                   RouteOsUi.dp(mActivity, 52));
    params.gravity = Gravity.BOTTOM | Gravity.END;
    params.rightMargin = RouteOsUi.dp(mActivity, 18);
    params.bottomMargin = RouteOsUi.dp(mActivity, 100);
    return params;
  }

  private View action(String icon, String title, String subtitle, int color, Runnable action)
  {
    LinearLayout card = new LinearLayout(mActivity);
    card.setOrientation(LinearLayout.VERTICAL);
    card.setGravity(Gravity.CENTER);
    card.setPadding(3, 5, 3, 5);
    card.setBackground(RouteOsUi.background(RouteOsUi.CARD, RouteOsUi.dp(mActivity, 15), Color.TRANSPARENT));
    TextView glyph = RouteOsUi.text(mActivity, icon, 23, color, true);
    glyph.setGravity(Gravity.CENTER);
    card.addView(glyph, new LinearLayout.LayoutParams(-1, RouteOsUi.dp(mActivity, 30)));
    TextView heading = RouteOsUi.text(mActivity, title, 12, Color.WHITE, true);
    heading.setGravity(Gravity.CENTER);
    card.addView(heading);
    TextView sub = RouteOsUi.text(mActivity, subtitle, 10, RouteOsUi.MUTED, false);
    sub.setGravity(Gravity.CENTER);
    card.addView(sub);
    RouteOsUi.pressable(card, action);
    return card;
  }

  private View navItem(String label, boolean selected, Runnable action)
  {
    TextView item = RouteOsUi.text(mActivity, label, 11, selected ? RouteOsUi.GREEN : RouteOsUi.MUTED, selected);
    item.setGravity(Gravity.CENTER);
    if (selected)
      item.setBackground(
          RouteOsUi.background(Color.argb(70, 0, 120, 91), RouteOsUi.dp(mActivity, 13), Color.TRANSPARENT));
    RouteOsUi.pressable(item, action);
    return item;
  }

  private String accountInitial()
  {
    String name = mActivity.getSharedPreferences("routeos", Activity.MODE_PRIVATE).getString("driver_name", "?");
    return name == null || name.trim().isEmpty() ? "?" : name.substring(0, 1).toUpperCase(java.util.Locale.ROOT);
  }

  public void refresh()
  {
    mExecutor.execute(() -> {
      JSONArray routes = null;
      Exception routeError = null;
      try
      {
        routes = RouteOsApi.getRoutes();
      }
      catch (Exception error)
      {
        routeError = error;
      }
      JSONObject ride = null;
      try
      {
        ride = RouteOsApi.getDriverActiveRide(mActivity);
      }
      catch (Exception error)
      {
        if (error.getMessage() != null && error.getMessage().contains("404"))
          RouteOsApi.clearActiveRide(mActivity);
      }
      final JSONArray finalRoutes = routes;
      final Exception finalError = routeError;
      final JSONObject finalRide = ride;
      runOnUiThread(() -> {
        renderRecentRoutes(finalRoutes, finalError);
        renderActiveRide(finalRide);
      });
    });
  }

  private void runOnUiThread(Runnable action)
  {
    mUi.post(() -> {
      if (mDestroyed || mActivity.isFinishing() || mActivity.isDestroyed())
        return;
      action.run();
    });
  }

  private void showRecentLoading()
  {
    mRecentRoutes.removeAllViews();
    TextView loading = RouteOsUi.text(mActivity, "Loading saved routes…", 13, RouteOsUi.MUTED, false);
    loading.setPadding(4, 14, 4, 14);
    mRecentRoutes.addView(loading);
  }

  private void renderRecentRoutes(JSONArray routes, Exception error)
  {
    mRecentRoutes.removeAllViews();
    if (error != null)
    {
      TextView failure =
          RouteOsUi.text(mActivity, "RouteOS backend unavailable", 13, Color.rgb(255, 110, 120), false);
      failure.setPadding(4, 14, 4, 14);
      mRecentRoutes.addView(failure);
      return;
    }
    if (routes == null || routes.length() == 0)
    {
      TextView empty = RouteOsUi.text(mActivity, "No routes yet. Record your first route.", 13, RouteOsUi.MUTED,
                                      false);
      empty.setPadding(4, 14, 4, 14);
      mRecentRoutes.addView(empty);
      return;
    }
    for (int index = 0; index < Math.min(3, routes.length()); index++)
    {
      JSONObject route = routes.optJSONObject(index);
      if (route == null)
        continue;
      LinearLayout card = new LinearLayout(mActivity);
      card.setGravity(Gravity.CENTER_VERTICAL);
      card.setPadding(RouteOsUi.dp(mActivity, 10), 0, RouteOsUi.dp(mActivity, 8), 0);
      card.setBackground(RouteOsUi.background(RouteOsUi.CARD, RouteOsUi.dp(mActivity, 13), Color.TRANSPARENT));

      TextView glyph = RouteOsUi.text(mActivity, "⌁", 21, RouteOsUi.GREEN, true);
      glyph.setGravity(Gravity.CENTER);
      card.addView(glyph, new LinearLayout.LayoutParams(RouteOsUi.dp(mActivity, 36), -1));

      LinearLayout copy = new LinearLayout(mActivity);
      copy.setOrientation(LinearLayout.VERTICAL);
      copy.setPadding(RouteOsUi.dp(mActivity, 10), 0, 0, 0);
      copy.addView(RouteOsUi.text(mActivity, route.optString("name", "Saved route"), 14, Color.WHITE, true));
      String endpoints = route.optString("origin", "Hub") + "  →  " + route.optString("destination", "Route");
      copy.addView(RouteOsUi.text(mActivity, endpoints, 11, RouteOsUi.MUTED, false));
      card.addView(copy, new LinearLayout.LayoutParams(0, -1, 1));

      TextView play = RouteOsUi.text(mActivity, "▶", 15, Color.WHITE, true);
      play.setGravity(Gravity.CENTER);
      card.addView(play, new LinearLayout.LayoutParams(RouteOsUi.dp(mActivity, 36), RouteOsUi.dp(mActivity, 36)));

      RouteOsUi.pressable(card, () -> mActivity.startActivity(new Intent(mActivity, RouteOsRoutesActivity.class)
                                                                   .putExtra("routeos_query",
                                                                             route.optString("name"))));
      LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, RouteOsUi.dp(mActivity, 60));
      params.setMargins(0, 0, 0, RouteOsUi.dp(mActivity, 6));
      mRecentRoutes.addView(card, params);
    }
  }

  private void renderActiveRide(JSONObject ride)
  {
    if (ride == null)
    {
      mActiveRidePanel.setVisibility(View.GONE);
      return;
    }
    mActiveRidePanel.setVisibility(View.VISIBLE);
    mActiveRideDetail.setText(ride.optString("route_name") + "  •  " + ride.optString("vehicle_number"));
    mActiveRidePrimary.setOnClickListener(v -> mHost.routeOsResumeRide(ride));
  }

  public void destroy()
  {
    mDestroyed = true;
    mExecutor.shutdownNow();
    mUi.removeCallbacksAndMessages(null);
  }
}
