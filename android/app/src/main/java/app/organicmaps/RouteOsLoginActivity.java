package app.organicmaps;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.os.Bundle;
import android.view.Gravity;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;
import androidx.annotation.Nullable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.json.JSONObject;

/** Deliberately small MVP account picker; authentication can replace this boundary later. */
public final class RouteOsLoginActivity extends Activity {
  private final ExecutorService executor = Executors.newSingleThreadExecutor();

  @Override public void onCreate(@Nullable Bundle state) {
    super.onCreate(state);
    getWindow().setStatusBarColor(RouteOsUi.BG);
    getWindow().setNavigationBarColor(RouteOsUi.BG);
    LinearLayout root = new LinearLayout(this);
    root.setOrientation(LinearLayout.VERTICAL);
    root.setGravity(Gravity.CENTER_HORIZONTAL);
    root.setPadding(RouteOsUi.dp(this, 24), RouteOsUi.dp(this, 72), RouteOsUi.dp(this, 24), RouteOsUi.dp(this, 32));
    root.setBackgroundColor(RouteOsUi.BG);

    TextView logo = RouteOsUi.text(this, "◉  RouteOS", 32, Color.WHITE, true); logo.setGravity(Gravity.CENTER);
    root.addView(logo, new LinearLayout.LayoutParams(-1, RouteOsUi.dp(this, 70)));
    TextView subtitle = RouteOsUi.text(this, "Drive. Track. Deliver.", 15, RouteOsUi.MUTED, false); subtitle.setGravity(Gravity.CENTER);
    root.addView(subtitle, new LinearLayout.LayoutParams(-1, RouteOsUi.dp(this, 44)));
    TextView prompt = RouteOsUi.text(this, "Quick login", 19, Color.WHITE, true);
    LinearLayout.LayoutParams promptParams = new LinearLayout.LayoutParams(-1, RouteOsUi.dp(this, 56)); promptParams.setMargins(0, RouteOsUi.dp(this, 42), 0, RouteOsUi.dp(this, 8)); root.addView(prompt, promptParams);
    root.addView(account("D", "Disha Patani", "Driver", false));
    root.addView(account("S", "Sukumara Kurup", "Driver", false));
    root.addView(account("T", "Thomachan Valiparambil", "Admin", true));
    TextView note = RouteOsUi.text(this, "RouteOS MVP accounts • no password required", 12, RouteOsUi.MUTED, false); note.setGravity(Gravity.CENTER);
    LinearLayout.LayoutParams noteParams = new LinearLayout.LayoutParams(-1, RouteOsUi.dp(this, 60)); noteParams.setMargins(0, RouteOsUi.dp(this, 20), 0, 0); root.addView(note, noteParams);
    setContentView(root);
  }

  private LinearLayout account(String initial, String name, String role, boolean admin) {
    LinearLayout card = new LinearLayout(this); card.setGravity(Gravity.CENTER_VERTICAL);
    card.setPadding(RouteOsUi.dp(this, 14), RouteOsUi.dp(this, 10), RouteOsUi.dp(this, 14), RouteOsUi.dp(this, 10));
    card.setBackground(RouteOsUi.background(admin ? Color.rgb(24, 31, 48) : RouteOsUi.CARD, RouteOsUi.dp(this, 18), admin ? Color.rgb(125, 101, 221) : RouteOsUi.STROKE));
    TextView avatar = RouteOsUi.text(this, initial, 20, Color.WHITE, true); avatar.setGravity(Gravity.CENTER);
    avatar.setBackground(RouteOsUi.background(admin ? Color.rgb(107, 83, 199) : Color.rgb(0, 125, 83), 100, Color.TRANSPARENT));
    card.addView(avatar, new LinearLayout.LayoutParams(RouteOsUi.dp(this, 48), RouteOsUi.dp(this, 48)));
    LinearLayout copy = new LinearLayout(this); copy.setOrientation(LinearLayout.VERTICAL); copy.setPadding(RouteOsUi.dp(this, 14), 0, 0, 0);
    copy.addView(RouteOsUi.text(this, name, 16, Color.WHITE, true));
    copy.addView(RouteOsUi.text(this, role, 13, admin ? Color.rgb(183, 168, 255) : RouteOsUi.GREEN, false));
    card.addView(copy, new LinearLayout.LayoutParams(0, -1, 1));
    card.addView(RouteOsUi.text(this, "›", 28, RouteOsUi.MUTED, false), new LinearLayout.LayoutParams(RouteOsUi.dp(this, 28), -1));
    RouteOsUi.pressable(card, () -> login(name));
    LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, RouteOsUi.dp(this, 84)); params.setMargins(0, RouteOsUi.dp(this, 6), 0, RouteOsUi.dp(this, 6)); card.setLayoutParams(params);
    return card;
  }

  private void login(String name) {
    executor.execute(() -> {
      try {
        JSONObject user = RouteOsApi.login(this, name);
        runOnUiThread(() -> {
          Intent intent;
          if ("admin".equals(user.optString("role")))
            intent = new Intent(this, MwmActivity.class).putExtra("routeos_admin", true).putExtra("routeos_skip_home", true);
          else
            intent = new Intent(this, RouteOsHomeActivity.class);
          startActivity(intent); finish();
        });
      } catch (Exception error) {
        runOnUiThread(() -> Toast.makeText(this, "Login failed: " + error.getMessage(), Toast.LENGTH_LONG).show());
      }
    });
  }

  @Override protected void onDestroy() { executor.shutdownNow(); super.onDestroy(); }
}
