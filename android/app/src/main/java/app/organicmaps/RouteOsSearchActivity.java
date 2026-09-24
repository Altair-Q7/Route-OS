package app.organicmaps;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.location.Location;
import android.os.Bundle;
import android.view.Gravity;
import android.view.inputmethod.EditorInfo;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import app.organicmaps.sdk.search.SearchEngine;
import app.organicmaps.sdk.search.SearchListener;
import app.organicmaps.sdk.search.SearchResult;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.json.JSONArray;
import org.json.JSONObject;

/** RouteOS search chrome backed by shared routes and Organic Maps' offline place search. */
public final class RouteOsSearchActivity extends Activity implements SearchListener {
  private final ExecutorService executor = Executors.newSingleThreadExecutor();
  private LinearLayout results;
  private EditText query;
  private long searchTimestamp;
  private JSONArray routeData = new JSONArray();
  private SearchResult[] placeData = new SearchResult[0];
  private String activeFilter = "";

  @Override public void onCreate(@Nullable Bundle state) {
    super.onCreate(state); getWindow().setStatusBarColor(RouteOsUi.BG); getWindow().setNavigationBarColor(RouteOsUi.BG);
    LinearLayout root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL); root.setPadding(RouteOsUi.dp(this, 14), RouteOsUi.dp(this, 24), RouteOsUi.dp(this, 14), RouteOsUi.dp(this, 12)); root.setBackgroundColor(RouteOsUi.BG);
    LinearLayout top = new LinearLayout(this); top.setGravity(Gravity.CENTER_VERTICAL);
    TextView back = RouteOsUi.text(this, "‹", 40, Color.WHITE, false); back.setGravity(Gravity.CENTER); RouteOsUi.pressable(back, this::finish); top.addView(back, new LinearLayout.LayoutParams(RouteOsUi.dp(this, 52), RouteOsUi.dp(this, 58)));
    top.addView(RouteOsUi.text(this, "Search", 21, Color.WHITE, true), new LinearLayout.LayoutParams(0, RouteOsUi.dp(this, 58), 1)); root.addView(top);
    query = new EditText(this); query.setSingleLine(); query.setImeOptions(EditorInfo.IME_ACTION_SEARCH); query.setHint("Search places or routes…"); query.setTextColor(Color.WHITE); query.setHintTextColor(RouteOsUi.MUTED); query.setPadding(RouteOsUi.dp(this, 18), 0, RouteOsUi.dp(this, 18), 0); query.setBackground(RouteOsUi.background(RouteOsUi.CARD, RouteOsUi.dp(this, 20), RouteOsUi.STROKE)); root.addView(query, new LinearLayout.LayoutParams(-1, RouteOsUi.dp(this, 58)));
    ScrollView scroll = new ScrollView(this); results = new LinearLayout(this); results.setOrientation(LinearLayout.VERTICAL); scroll.addView(results); root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1)); setContentView(root);
    SearchEngine.INSTANCE.addListener(this);
    query.setOnEditorActionListener((view, action, event) -> { search(view.getText().toString()); return true; });
    String initial = getIntent().getStringExtra("routeos_query"); if (initial != null) { query.setText(initial); search(initial); }
  }

  private void search(String value) {
    String text = value.trim(); if (text.isEmpty()) return; activeFilter = text; routeData = new JSONArray(); placeData = new SearchResult[0]; results.removeAllViews(); results.addView(section("Searching RouteOS and Organic Maps…"));
    searchTimestamp = System.nanoTime(); Location location = MwmApplication.from(this).getLocationHelper().getSavedLocation();
    SearchEngine.INSTANCE.search(this, text, false, searchTimestamp, location != null, location == null ? 0 : location.getLatitude(), location == null ? 0 : location.getLongitude());
    executor.execute(() -> { try { JSONArray routes = RouteOsApi.getRoutes(); runOnUiThread(() -> { routeData = routes; renderResults(); }); } catch (Exception ignored) {} });
  }

  private TextView section(String title) { TextView view = RouteOsUi.text(this, title, 14, RouteOsUi.MUTED, true); view.setPadding(RouteOsUi.dp(this, 8), RouteOsUi.dp(this, 16), RouteOsUi.dp(this, 8), RouteOsUi.dp(this, 8)); return view; }

  private void renderResults() {
    results.removeAllViews(); String filter = activeFilter;
    results.addView(section("SAVED ROUTES"));
    for (int i = 0; i < routeData.length(); i++) { JSONObject route = routeData.optJSONObject(i); if (!route.optString("name").toLowerCase(java.util.Locale.ROOT).contains(filter.toLowerCase(java.util.Locale.ROOT))) continue; TextView row = resultRow("⌁  " + route.optString("name"), "Shared by " + route.optString("recorder_name")); RouteOsUi.pressable(row, () -> startActivity(new Intent(this, RouteOsRoutesActivity.class).putExtra("routeos_query", route.optString("name")))); results.addView(row); }
    results.addView(section("PLACES")); int count = Math.min(placeData.length, 12);
    for (int i = 0; i < count; i++) { SearchResult item = placeData[i]; if (item.type == SearchResult.TYPE_PURE_SUGGEST) continue; final int index = i; String detail = placeDetail(item); TextView row = resultRow("⌖  " + item.getTitle(this), detail); RouteOsUi.pressable(row, () -> { SearchEngine.INSTANCE.showResult(index); startActivity(new Intent(this, MwmActivity.class).putExtra("routeos_map", true).putExtra("routeos_skip_home", true)); finish(); }); results.addView(row); }
  }

  @Override public void onResultsUpdate(@NonNull SearchResult[] found, long timestamp) {
    if (timestamp != searchTimestamp) return; runOnUiThread(() -> { placeData = found; renderResults(); });
  }

  /** Search results may carry no region (or an empty one), which must not leak a "null" row. */
  private String placeDetail(SearchResult item) {
    if (item.description == null || item.description.region == null || item.description.region.isEmpty()) return "Organic Maps";
    return item.description.region;
  }

  private TextView resultRow(String title, String detail) { TextView row = RouteOsUi.text(this, title + "\n" + detail, 15, Color.WHITE, false); row.setPadding(RouteOsUi.dp(this, 16), RouteOsUi.dp(this, 10), RouteOsUi.dp(this, 16), RouteOsUi.dp(this, 10)); row.setBackground(RouteOsUi.background(RouteOsUi.CARD, RouteOsUi.dp(this, 14), Color.TRANSPARENT)); LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, RouteOsUi.dp(this, 72)); params.setMargins(0, RouteOsUi.dp(this, 4), 0, RouteOsUi.dp(this, 4)); row.setLayoutParams(params); return row; }

  @Override protected void onDestroy() { SearchEngine.INSTANCE.removeListener(this); SearchEngine.INSTANCE.cancel(); executor.shutdownNow(); super.onDestroy(); }
}
