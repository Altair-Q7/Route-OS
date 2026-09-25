package app.routeos;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Rect;
import android.graphics.Typeface;
import android.graphics.drawable.BitmapDrawable;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.view.Gravity;
import android.view.View;
import android.widget.LinearLayout;
import android.widget.TextView;
import androidx.annotation.NonNull;

/** Shared RouteOS palette and view factories. */
public final class RouteOsUi
{
  public static final int BG = Color.rgb(9, 15, 22);
  public static final int PANEL = Color.argb(238, 17, 25, 35);
  public static final int CARD = Color.rgb(24, 34, 45);
  public static final int STROKE = Color.rgb(54, 68, 82);
  public static final int GREEN = Color.rgb(19, 230, 157);
  public static final int MUTED = Color.rgb(168, 181, 194);
  public static final int DANGER = Color.rgb(244, 54, 62);

  private RouteOsUi() {}

  public static int dp(Context context, int value)
  {
    return Math.round(value * context.getResources().getDisplayMetrics().density);
  }

  public static GradientDrawable background(int color, float radius, int strokeColor)
  {
    GradientDrawable drawable = new GradientDrawable();
    drawable.setColor(color);
    drawable.setCornerRadius(radius);
    if (strokeColor != Color.TRANSPARENT)
      drawable.setStroke(1, strokeColor);
    return drawable;
  }

  public static TextView text(Context context, String value, float size, int color, boolean bold)
  {
    TextView text = new TextView(context);
    text.setText(value);
    text.setTextSize(size);
    text.setTextColor(color);
    text.setGravity(Gravity.CENTER_VERTICAL);
    if (bold)
      text.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
    return text;
  }

  public static LinearLayout.LayoutParams params(int width, int height, float weight, Context context)
  {
    LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(width, height, weight);
    params.setMargins(dp(context, 4), dp(context, 4), dp(context, 4), dp(context, 4));
    return params;
  }

  public static void pressable(View view, Runnable action)
  {
    view.setClickable(true);
    view.setFocusable(true);
    view.setOnClickListener(v -> action.run());
  }

  /** RouteOS brand mark: an open ring with a solid centre, scaled to whatever bounds it gets. */
  public static Drawable ring()
  {
    return new RingDrawable();
  }

  /** Renders a glyph to a drawable so it can be used as a compound/leading icon. */
  public static Drawable glyph(Context context, String symbol, int color)
  {
    TextView label = new TextView(context);
    label.setText(symbol);
    label.setTextSize(15);
    label.setTextColor(color);
    label.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
    label.measure(View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED),
                  View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED));
    int width = Math.max(1, label.getMeasuredWidth());
    int height = Math.max(1, label.getMeasuredHeight());
    label.layout(0, 0, width, height);
    Bitmap bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
    label.draw(new Canvas(bitmap));
    BitmapDrawable drawable = new BitmapDrawable(context.getResources(), bitmap);
    drawable.setBounds(0, 0, width, height);
    return drawable;
  }

  private static final class RingDrawable extends Drawable
  {
    private final Paint mStroke = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint mFill = new Paint(Paint.ANTI_ALIAS_FLAG);

    RingDrawable()
    {
      mStroke.setStyle(Paint.Style.STROKE);
      mStroke.setStrokeCap(Paint.Cap.ROUND);
      mStroke.setColor(GREEN);
      mFill.setStyle(Paint.Style.FILL);
      mFill.setColor(GREEN);
    }

    @Override
    public void draw(@NonNull Canvas canvas)
    {
      Rect bounds = getBounds();
      float size = Math.min(bounds.width(), bounds.height());
      if (size <= 0)
        return;
      float cx = bounds.exactCenterX();
      float cy = bounds.exactCenterY();
      mStroke.setStrokeWidth(size * 0.17f);
      float radius = size * 0.36f;
      // Gap centred on the top of the ring, matching the RouteOS brand mark.
      canvas.drawArc(cx - radius, cy - radius, cx + radius, cy + radius, 300, 300, false, mStroke);
      float dot = size * 0.17f;
      canvas.drawCircle(cx, cy, dot, mFill);
    }

    @Override
    public void setAlpha(int alpha)
    {
      mStroke.setAlpha(alpha);
      mFill.setAlpha(alpha);
    }

    @Override
    public void setColorFilter(@androidx.annotation.Nullable android.graphics.ColorFilter colorFilter)
    {
      mStroke.setColorFilter(colorFilter);
      mFill.setColorFilter(colorFilter);
    }

    @Override
    public int getOpacity()
    {
      return android.graphics.PixelFormat.TRANSLUCENT;
    }
  }
}
