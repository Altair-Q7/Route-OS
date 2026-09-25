package app.routeos;

import android.app.Activity;
import android.graphics.Color;
import android.graphics.Typeface;
import android.location.Location;
import android.text.TextUtils;
import android.view.Gravity;
import android.view.View;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import app.organicmaps.R;
import app.organicmaps.sdk.routing.RoutingInfo;
import app.organicmaps.sdk.sound.TtsPlayer;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

/**
 * RouteOS navigation chrome drawn over the native map.
 *
 * <p>Every number shown here is read from Organic Maps' own routing engine — maneuver, remaining
 * time, remaining distance, speed limit and voice guidance are not recomputed by RouteOS.
 */
public final class RouteOsNavigationOverlay
{
  public interface Host
  {
    void routeOsEndRide();

    void routeOsOpenVoiceSettings();
  }

  private final Activity mActivity;
  private final Host mHost;
  private final String mRouteName;

  private FrameLayout mRoot;
  private ImageView mManeuverIcon;
  private TextView mManeuverDistance;
  private TextView mManeuverStreet;
  private TextView mRouteLabel;
  private ImageView mVoice;
  private TextView mEta;
  private TextView mEtaDetails;
  private TextView mSpeed;
  private TextView mSpeedLimit;
  private TextView mStatus;

  public RouteOsNavigationOverlay(@NonNull Activity activity, @NonNull Host host, @NonNull String routeName)
  {
    mActivity = activity;
    mHost = host;
    mRouteName = routeName;
  }

  public FrameLayout build()
  {
    if (mRoot != null)
      return mRoot;

    mRoot = new FrameLayout(mActivity);

    mRoot.addView(buildManeuverCard(), maneuverParams());
    mRoot.addView(buildSpeed(), speedParams());
    mRoot.addView(buildSpeedLimit(), speedLimitParams());
    mRoot.addView(buildStatusStrip(), statusParams());
    mRoot.addView(buildSummary(), summaryParams());
    return mRoot;
  }

  private View buildManeuverCard()
  {
    LinearLayout card = new LinearLayout(mActivity);
    card.setGravity(Gravity.CENTER_VERTICAL);
    card.setPadding(RouteOsUi.dp(mActivity, 16), RouteOsUi.dp(mActivity, 12), RouteOsUi.dp(mActivity, 12),
                    RouteOsUi.dp(mActivity, 12));
    card.setBackground(RouteOsUi.background(Color.rgb(7, 96, 68), RouteOsUi.dp(mActivity, 20), Color.TRANSPARENT));

    mManeuverIcon = new ImageView(mActivity);
    mManeuverIcon.setScaleType(ImageView.ScaleType.FIT_CENTER);
    card.addView(mManeuverIcon, new LinearLayout.LayoutParams(RouteOsUi.dp(mActivity, 44), RouteOsUi.dp(mActivity, 44)));

    LinearLayout copy = new LinearLayout(mActivity);
    copy.setOrientation(LinearLayout.VERTICAL);
    copy.setPadding(RouteOsUi.dp(mActivity, 12), 0, RouteOsUi.dp(mActivity, 8), 0);
    mManeuverDistance = RouteOsUi.text(mActivity, "Starting…", 24, Color.WHITE, true);
    mManeuverStreet = RouteOsUi.text(mActivity, "", 13, Color.rgb(198, 255, 236), false);
    mRouteLabel = RouteOsUi.text(mActivity, mRouteName, 12, Color.rgb(160, 240, 214), false);
    copy.addView(mManeuverDistance);
    copy.addView(mManeuverStreet);
    copy.addView(mRouteLabel);
    card.addView(copy, new LinearLayout.LayoutParams(0, -2, 1));

    mVoice = new ImageView(mActivity);
    mVoice.setScaleType(ImageView.ScaleType.CENTER_INSIDE);
    mVoice.setPadding(RouteOsUi.dp(mActivity, 10), RouteOsUi.dp(mActivity, 10), RouteOsUi.dp(mActivity, 10),
                      RouteOsUi.dp(mActivity, 10));
    mVoice.setBackground(RouteOsUi.background(Color.argb(70, 255, 255, 255), 100, Color.TRANSPARENT));
    mVoice.setOnClickListener(v -> {
      final TtsPlayer.State state = TtsPlayer.getState();
      if (state == TtsPlayer.State.UNAVAILABLE || state == TtsPlayer.State.NEEDS_LANGUAGE)
      {
        mHost.routeOsOpenVoiceSettings();
        return;
      }
      if (state == TtsPlayer.State.READY_ON || state == TtsPlayer.State.READY_OFF)
        TtsPlayer.setEnabled(!TtsPlayer.isEnabled());
      refreshVoiceIcon();
    });
    card.addView(mVoice, new LinearLayout.LayoutParams(RouteOsUi.dp(mActivity, 44), RouteOsUi.dp(mActivity, 44)));
    refreshVoiceIcon();
    return card;
  }

  private void refreshVoiceIcon()
  {
    boolean on = TtsPlayer.getState() == TtsPlayer.State.READY_ON && TtsPlayer.isEnabled();
    mVoice.setImageResource(on ? R.drawable.ic_voice_on : R.drawable.ic_voice_off);
    mVoice.setAlpha(on ? 1f : 0.65f);
  }

  private View buildSpeed()
  {
    mSpeed = metricCircle(Color.WHITE);
    return mSpeed;
  }

  private View buildSpeedLimit()
  {
    mSpeedLimit = metricCircle(Color.rgb(255, 92, 92));
    mSpeedLimit.setVisibility(View.GONE);
    return mSpeedLimit;
  }

  private TextView metricCircle(int color)
  {
    TextView view = RouteOsUi.text(mActivity, "", 17, color, true);
    view.setGravity(Gravity.CENTER);
    view.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
    view.setBackground(RouteOsUi.background(Color.argb(240, 10, 16, 23), 100, RouteOsUi.STROKE));
    return view;
  }

  private View buildStatusStrip()
  {
    mStatus = RouteOsUi.text(mActivity, "ROUTE ACTIVE  •  Guidance on", 11, RouteOsUi.GREEN, true);
    mStatus.setGravity(Gravity.CENTER);
    mStatus.setPadding(RouteOsUi.dp(mActivity, 12), 0, RouteOsUi.dp(mActivity, 12), 0);
    mStatus.setBackground(RouteOsUi.background(Color.argb(240, 10, 16, 23), RouteOsUi.dp(mActivity, 14),
                                                RouteOsUi.STROKE));
    return mStatus;
  }

  private View buildSummary()
  {
    LinearLayout sheet = new LinearLayout(mActivity);
    sheet.setGravity(Gravity.CENTER_VERTICAL);
    sheet.setPadding(RouteOsUi.dp(mActivity, 20), RouteOsUi.dp(mActivity, 8), RouteOsUi.dp(mActivity, 14),
                     RouteOsUi.dp(mActivity, 8));
    sheet.setBackground(
        RouteOsUi.background(Color.argb(248, 10, 16, 23), RouteOsUi.dp(mActivity, 22), RouteOsUi.STROKE));

    LinearLayout details = new LinearLayout(mActivity);
    details.setOrientation(LinearLayout.VERTICAL);
    mEta = RouteOsUi.text(mActivity, "—", 30, RouteOsUi.GREEN, true);
    mEtaDetails = RouteOsUi.text(mActivity, "Waiting for the route…", 13, RouteOsUi.MUTED, false);
    details.addView(mEta);
    details.addView(mEtaDetails);
    sheet.addView(details, new LinearLayout.LayoutParams(0, -2, 1));

    TextView end = RouteOsUi.text(mActivity, "End", 17, Color.WHITE, true);
    end.setGravity(Gravity.CENTER);
    end.setBackground(RouteOsUi.background(RouteOsUi.DANGER, RouteOsUi.dp(mActivity, 20), Color.TRANSPARENT));
    RouteOsUi.pressable(end, () -> mHost.routeOsEndRide());
    sheet.addView(end, new LinearLayout.LayoutParams(RouteOsUi.dp(mActivity, 104), RouteOsUi.dp(mActivity, 56)));
    return sheet;
  }

  private FrameLayout.LayoutParams maneuverParams()
  {
    FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(-1, RouteOsUi.dp(mActivity, 104));
    params.gravity = Gravity.TOP;
    params.setMargins(RouteOsUi.dp(mActivity, 14), RouteOsUi.dp(mActivity, 30), RouteOsUi.dp(mActivity, 14), 0);
    return params;
  }

  private FrameLayout.LayoutParams speedParams()
  {
    FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(RouteOsUi.dp(mActivity, 64), RouteOsUi.dp(mActivity, 64));
    params.gravity = Gravity.BOTTOM | Gravity.START;
    params.setMargins(RouteOsUi.dp(mActivity, 16), 0, 0, RouteOsUi.dp(mActivity, 178));
    return params;
  }

  private FrameLayout.LayoutParams speedLimitParams()
  {
    FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(RouteOsUi.dp(mActivity, 64), RouteOsUi.dp(mActivity, 64));
    params.gravity = Gravity.BOTTOM | Gravity.END;
    params.setMargins(0, 0, RouteOsUi.dp(mActivity, 16), RouteOsUi.dp(mActivity, 178));
    return params;
  }

  private FrameLayout.LayoutParams statusParams()
  {
    FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(-1, RouteOsUi.dp(mActivity, 30));
    params.gravity = Gravity.BOTTOM;
    params.setMargins(RouteOsUi.dp(mActivity, 16), 0, RouteOsUi.dp(mActivity, 16), RouteOsUi.dp(mActivity, 120));
    return params;
  }

  private FrameLayout.LayoutParams summaryParams()
  {
    FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(-1, RouteOsUi.dp(mActivity, 88));
    params.gravity = Gravity.BOTTOM;
    params.setMargins(RouteOsUi.dp(mActivity, 12), 0, RouteOsUi.dp(mActivity, 12), RouteOsUi.dp(mActivity, 18));
    return params;
  }

  /** Feeds the overlay with Organic Maps' own route following info; nothing is derived here. */
  public void update(@Nullable RoutingInfo info, @Nullable Location location)
  {
    if (mRoot == null)
      return;

    if (info == null)
    {
      mManeuverDistance.setText("Starting…");
      mManeuverStreet.setText(mRouteName);
      mEta.setText("—");
      mEtaDetails.setText("Waiting for the route…");
      mSpeed.setText("--");
      mSpeedLimit.setVisibility(View.GONE);
      return;
    }

    mManeuverIcon.setImageResource(info.carDirection.getTurnRes(info.exitNum));
    if (info.carDirection == app.organicmaps.sdk.routing.CarDirection.ReachedYourDestination)
    {
      mManeuverDistance.setText("Arrived");
      mManeuverStreet.setText(mRouteName);
    }
    else
    {
      mManeuverDistance.setText("in " + info.distToTurn.toString(mActivity));
      String street = TextUtils.isEmpty(info.nextStreet) ? info.currentStreet : info.nextStreet;
      mManeuverStreet.setText(street == null || street.isEmpty() ? mRouteName : street);
    }

    mEta.setText(formatRemainingTime(info.totalTimeInSeconds));
    mEtaDetails.setText(info.distToTarget.toString(mActivity) + "  •  " + arrivalTime(info.totalTimeInSeconds));

    if (location != null && location.hasSpeed() && location.getSpeed() >= 0)
      mSpeed.setText(Math.round(location.getSpeed() * 3.6f) + "\nkm/h");

    if (info.speedLimitMps > 0)
    {
      mSpeedLimit.setVisibility(View.VISIBLE);
      mSpeedLimit.setText(Math.round(info.speedLimitMps * 3.6f) + "");
      mSpeedLimit.setBackground(RouteOsUi.background(Color.argb(240, 255, 255, 255), 100, Color.rgb(226, 61, 61)));
      mSpeedLimit.setTextColor(Color.rgb(20, 24, 30));
    }
    else
      mSpeedLimit.setVisibility(View.GONE);

    mStatus.setText("ROUTE ACTIVE  •  " + mRouteName);
  }

  static String formatRemainingTime(int seconds)
  {
    int hours = seconds / 3600;
    int minutes = (seconds % 3600) / 60;
    if (hours > 0)
      return hours + " h " + minutes + " min";
    return Math.max(1, minutes) + " min";
  }

  static String arrivalTime(int seconds)
  {
    Date arrival = new Date(System.currentTimeMillis() + seconds * 1000L);
    return new SimpleDateFormat("h:mm a", Locale.getDefault()).format(arrival);
  }

  public void destroy()
  {
    mRoot = null;
  }
}
