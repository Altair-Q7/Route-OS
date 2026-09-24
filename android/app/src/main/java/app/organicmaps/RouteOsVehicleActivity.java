package app.organicmaps;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;
import androidx.annotation.Nullable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.json.JSONObject;

/** One-screen vehicle choice; vehicle values belong to a ride, not a fleet system. */
public final class RouteOsVehicleActivity extends Activity {
  private final ExecutorService executor = Executors.newSingleThreadExecutor();
  private String vehicleType = "Car";
  private LinearLayout types;
  private EditText number;
  private TextView startButton;

  @Override public void onCreate(@Nullable Bundle state) {
    super.onCreate(state);
    getWindow().setStatusBarColor(RouteOsUi.BG); getWindow().setNavigationBarColor(RouteOsUi.BG);
    LinearLayout root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL);
    root.setPadding(RouteOsUi.dp(this, 16), RouteOsUi.dp(this, 24), RouteOsUi.dp(this, 16), RouteOsUi.dp(this, 18)); root.setBackgroundColor(RouteOsUi.BG);
    LinearLayout header = new LinearLayout(this); header.setGravity(Gravity.CENTER_VERTICAL);
    TextView back = RouteOsUi.text(this, "‹", 40, Color.WHITE, false); back.setGravity(Gravity.CENTER); RouteOsUi.pressable(back, this::finish); header.addView(back, new LinearLayout.LayoutParams(RouteOsUi.dp(this, 50), RouteOsUi.dp(this, 58)));
    TextView title = RouteOsUi.text(this, "Select Vehicle", 21, Color.WHITE, true); title.setGravity(Gravity.CENTER); header.addView(title, new LinearLayout.LayoutParams(0, RouteOsUi.dp(this, 58), 1)); header.addView(new View(this), new LinearLayout.LayoutParams(RouteOsUi.dp(this, 50), 1)); root.addView(header);
    root.addView(RouteOsUi.text(this, getIntent().getStringExtra("route_name"), 14, RouteOsUi.MUTED, false), new LinearLayout.LayoutParams(-1, RouteOsUi.dp(this, 48)));
    vehicleType = getSharedPreferences("routeos", MODE_PRIVATE).getString("last_vehicle_type", "Car");
    types = new LinearLayout(this); root.addView(types, new LinearLayout.LayoutParams(-1, RouteOsUi.dp(this, 102))); renderTypes();
    TextView label = RouteOsUi.text(this, "Vehicle Number", 14, Color.WHITE, true); LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, RouteOsUi.dp(this, 45)); lp.setMargins(0, RouteOsUi.dp(this, 18), 0, 0); root.addView(label, lp);
    number = new EditText(this); number.setSingleLine(); number.setHint("KL 06 AB 1234"); number.setText(getSharedPreferences("routeos", MODE_PRIVATE).getString("last_vehicle_number", "")); number.setTextColor(Color.WHITE); number.setHintTextColor(RouteOsUi.MUTED); number.setTextSize(16); number.setPadding(RouteOsUi.dp(this, 18), 0, RouteOsUi.dp(this, 18), 0); number.setBackground(RouteOsUi.background(RouteOsUi.CARD, RouteOsUi.dp(this, 17), RouteOsUi.STROKE)); root.addView(number, new LinearLayout.LayoutParams(-1, RouteOsUi.dp(this, 58)));
    root.addView(new View(this), new LinearLayout.LayoutParams(-1, 0, 1));
    startButton = RouteOsUi.text(this, "Start Ride  ›", 18, Color.rgb(2, 36, 27), true); startButton.setGravity(Gravity.CENTER); startButton.setBackground(RouteOsUi.background(RouteOsUi.GREEN, RouteOsUi.dp(this, 28), Color.TRANSPARENT)); RouteOsUi.pressable(startButton, this::startRide); root.addView(startButton, new LinearLayout.LayoutParams(-1, RouteOsUi.dp(this, 62)));
    setContentView(root);
  }

  private void renderTypes() {
    types.removeAllViews();
    for (String type : new String[] {"Car", "Bike", "Van", "Truck"}) {
      boolean active = type.equals(vehicleType); TextView view = RouteOsUi.text(this, symbol(type) + "\n" + type, 14, active ? RouteOsUi.GREEN : RouteOsUi.MUTED, active); view.setGravity(Gravity.CENTER);
      view.setBackground(RouteOsUi.background(active ? Color.rgb(0, 91, 64) : RouteOsUi.CARD, RouteOsUi.dp(this, 15), active ? RouteOsUi.GREEN : Color.TRANSPARENT)); RouteOsUi.pressable(view, () -> { vehicleType = type; renderTypes(); }); types.addView(view, RouteOsUi.params(0, RouteOsUi.dp(this, 92), 1, this));
    }
  }

  private String symbol(String type) { return switch (type) { case "Bike" -> "♞"; case "Van" -> "▣"; case "Truck" -> "▰"; default -> "▱"; }; }

  private void startRide() {
    String vehicleNumber = number.getText().toString().trim();
    if (vehicleNumber.isEmpty()) { number.setError("Enter a vehicle number"); return; }
    long routeId = getIntent().getLongExtra("route_id", 0); String routeName = getIntent().getStringExtra("route_name");
    double destinationLat = getIntent().getDoubleExtra("destination_lat", Double.NaN); double destinationLon = getIntent().getDoubleExtra("destination_lon", Double.NaN);
    final String selectedType = vehicleType;
    startButton.setEnabled(false); startButton.setAlpha(0.65f); startButton.setText("Starting ride…");
    executor.execute(() -> {
      try {
        JSONObject ride = RouteOsApi.startRide(this, routeId, selectedType, vehicleNumber);
        getSharedPreferences("routeos", MODE_PRIVATE).edit()
            .putString("last_vehicle_type", selectedType).putString("last_vehicle_number", vehicleNumber)
            .putLong("active_route_id", routeId).putString("active_route_name", routeName)
            .putFloat("active_destination_lat", (float) destinationLat).putFloat("active_destination_lon", (float) destinationLon).apply();
        runOnUiThread(() -> { Intent map = new Intent(this, MwmActivity.class).putExtra("routeos_start_ride", true).putExtra("routeos_skip_home", true).putExtra("routeos_route_name", routeName).putExtra("routeos_ride_id", ride.optLong("id")).putExtra("routeos_destination_lat", destinationLat).putExtra("routeos_destination_lon", destinationLon); startActivity(map); finish(); });
      } catch (Exception error) { runOnUiThread(() -> { startButton.setEnabled(true); startButton.setAlpha(1f); startButton.setText("Start Ride  ›"); Toast.makeText(this, "Could not start ride: " + error.getMessage(), Toast.LENGTH_LONG).show(); }); }
    });
  }

  @Override protected void onDestroy() { executor.shutdownNow(); super.onDestroy(); }
}
