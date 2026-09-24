package app.organicmaps;

import android.content.Context;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.view.Gravity;
import android.view.View;
import android.widget.LinearLayout;
import android.widget.TextView;

final class RouteOsUi {
  static final int BG = Color.rgb(9, 15, 22);
  static final int PANEL = Color.argb(238, 17, 25, 35);
  static final int CARD = Color.rgb(24, 34, 45);
  static final int STROKE = Color.rgb(54, 68, 82);
  static final int GREEN = Color.rgb(19, 230, 157);
  static final int MUTED = Color.rgb(168, 181, 194);

  private RouteOsUi() {}

  static int dp(Context context, int value) {
    return Math.round(value * context.getResources().getDisplayMetrics().density);
  }

  static GradientDrawable background(int color, float radius, int strokeColor) {
    GradientDrawable drawable = new GradientDrawable();
    drawable.setColor(color);
    drawable.setCornerRadius(radius);
    if (strokeColor != Color.TRANSPARENT) drawable.setStroke(1, strokeColor);
    return drawable;
  }

  static TextView text(Context context, String value, float size, int color, boolean bold) {
    TextView text = new TextView(context);
    text.setText(value);
    text.setTextSize(size);
    text.setTextColor(color);
    text.setGravity(Gravity.CENTER_VERTICAL);
    if (bold) text.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
    return text;
  }

  static LinearLayout.LayoutParams params(int width, int height, float weight, Context context) {
    LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(width, height, weight);
    params.setMargins(dp(context, 4), dp(context, 4), dp(context, 4), dp(context, 4));
    return params;
  }

  static void pressable(View view, Runnable action) {
    view.setClickable(true);
    view.setFocusable(true);
    view.setOnClickListener(v -> action.run());
  }
}
