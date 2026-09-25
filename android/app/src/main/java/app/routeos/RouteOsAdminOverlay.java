package app.routeos;

import android.app.Activity;
import android.graphics.Color;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import androidx.annotation.NonNull;
import app.organicmaps.sdk.Framework;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.RejectedExecutionException;
import org.json.JSONArray;
import org.json.JSONObject;

/** RouteOS admin live-ride surface hosted above the native map. */
public final class RouteOsAdminOverlay
{
  public interface Host
  {
    void routeOsAdminLogout();
  }

  private final Activity mActivity;
  private final Host mHost;
  private final Handler mUi = new Handler(Looper.getMainLooper());
  private final ExecutorService mExecutor = Executors.newSingleThreadExecutor();
  private final Runnable mPoll = this::loadActiveRides;
  private volatile boolean mStopped;
  private FrameLayout mRoot;
  private TextView mStatus;
  private TextView mMarker;
  private TextView mMarkerLabel;

  public RouteOsAdminOverlay(@NonNull Activity activity, @NonNull Host host)
  {
    mActivity = activity;
    mHost = host;
  }

  public FrameLayout build()
  {
    if (mRoot != null)
      return mRoot;

    mRoot = new FrameLayout(mActivity);
    addHeader();

    mMarker = RouteOsUi.text(mActivity, "●", 44, Color.rgb(255, 78, 92), true);
    mMarker.setGravity(Gravity.CENTER);
    mMarker.setVisibility(View.GONE);
    FrameLayout.LayoutParams markerParams = new FrameLayout.LayoutParams(RouteOsUi.dp(mActivity, 72),
                                                                          RouteOsUi.dp(mActivity, 72));
    markerParams.gravity = Gravity.CENTER;
    mRoot.addView(mMarker, markerParams);

    mMarkerLabel = RouteOsUi.text(mActivity, "", 13, Color.WHITE, true);
    mMarkerLabel.setGravity(Gravity.CENTER);
    mMarkerLabel.setVisibility(View.GONE);
    mMarkerLabel.setBackground(RouteOsUi.background(Color.argb(235, 8, 17, 24), RouteOsUi.dp(mActivity, 14),
                                                    RouteOsUi.STROKE));
    FrameLayout.LayoutParams labelParams = new FrameLayout.LayoutParams(-2, RouteOsUi.dp(mActivity, 34));
    labelParams.gravity = Gravity.CENTER;
    labelParams.topMargin = RouteOsUi.dp(mActivity, 78);
    mRoot.addView(mMarkerLabel, labelParams);

    LinearLayout panel = new LinearLayout(mActivity);
    panel.setOrientation(LinearLayout.VERTICAL);
    panel.setPadding(RouteOsUi.dp(mActivity, 18), RouteOsUi.dp(mActivity, 12), RouteOsUi.dp(mActivity, 18),
                     RouteOsUi.dp(mActivity, 12));
    panel.setBackground(RouteOsUi.background(Color.argb(248, 8, 17, 24), RouteOsUi.dp(mActivity, 22),
                                              RouteOsUi.STROKE));
    mStatus = RouteOsUi.text(mActivity, "Checking live rides…", 15, Color.WHITE, true);
    panel.addView(mStatus, new LinearLayout.LayoutParams(-1, 0, 1));

    LinearLayout controls = new LinearLayout(mActivity);
    TextView refresh = button("Refresh", Color.rgb(0, 133, 89));
    refresh.setOnClickListener(v -> loadActiveRides());
    controls.addView(refresh, RouteOsUi.params(0, RouteOsUi.dp(mActivity, 46), 1, mActivity));
    TextView logout = button("Log out", Color.rgb(42, 54, 65));
    logout.setOnClickListener(v -> mHost.routeOsAdminLogout());
    controls.addView(logout, RouteOsUi.params(0, RouteOsUi.dp(mActivity, 46), 1, mActivity));
    panel.addView(controls, new LinearLayout.LayoutParams(-1, RouteOsUi.dp(mActivity, 54)));

    FrameLayout.LayoutParams panelParams = new FrameLayout.LayoutParams(-1, RouteOsUi.dp(mActivity, 178));
    panelParams.gravity = Gravity.BOTTOM;
    panelParams.setMargins(RouteOsUi.dp(mActivity, 12), 0, RouteOsUi.dp(mActivity, 12), RouteOsUi.dp(mActivity, 18));
    mRoot.addView(panel, panelParams);
    return mRoot;
  }

  private void addHeader()
  {
    LinearLayout header = new LinearLayout(mActivity);
    header.setOrientation(LinearLayout.VERTICAL);
    header.setPadding(RouteOsUi.dp(mActivity, 20), RouteOsUi.dp(mActivity, 12), RouteOsUi.dp(mActivity, 20),
                      RouteOsUi.dp(mActivity, 12));
    header.setBackground(RouteOsUi.background(Color.argb(246, 8, 17, 24), RouteOsUi.dp(mActivity, 18),
                                               RouteOsUi.STROKE));
    header.addView(RouteOsUi.text(mActivity, "RouteOS Live Tracking", 21, Color.WHITE, true));
    header.addView(RouteOsUi.text(mActivity, "Drivers currently on a ride", 13, RouteOsUi.MUTED, false));
    FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(-1, RouteOsUi.dp(mActivity, 82));
    params.gravity = Gravity.TOP;
    params.setMargins(RouteOsUi.dp(mActivity, 14), RouteOsUi.dp(mActivity, 34), RouteOsUi.dp(mActivity, 14), 0);
    mRoot.addView(header, params);
  }

  private TextView button(String label, int color)
  {
    TextView view = RouteOsUi.text(mActivity, label, 15, Color.WHITE, true);
    view.setGravity(Gravity.CENTER);
    view.setBackground(RouteOsUi.background(color, RouteOsUi.dp(mActivity, 20), Color.TRANSPARENT));
    return view;
  }

  public void start()
  {
    if (mStopped)
      return;
    loadActiveRides();
  }

  private void loadActiveRides()
  {
    if (mStopped || mExecutor.isShutdown())
      return;
    try
    {
      mExecutor.execute(() -> {
        try
        {
          JSONArray rides = RouteOsApi.getActiveRides();
          mUi.post(() -> render(rides));
        }
        catch (Exception error)
        {
          mUi.post(() -> {
            if (mStopped)
              return;
            if (mStatus != null)
              mStatus.setText("Live tracking unavailable");
            schedulePoll(5000);
          });
        }
      });
    }
    catch (RejectedExecutionException ignored)
    {
      // stop() may win the race after the shutdown guard above.
    }
  }

  private void schedulePoll(long delayMillis)
  {
    if (mStopped || mExecutor.isShutdown())
      return;
    mUi.removeCallbacks(mPoll);
    mUi.postDelayed(mPoll, delayMillis);
  }

  private void render(@NonNull JSONArray rides)
  {
    if (mStopped || mRoot == null || !mRoot.isAttachedToWindow())
      return;
    if (rides.length() == 0)
    {
      mMarker.setVisibility(View.GONE);
      mMarkerLabel.setVisibility(View.GONE);
      mStatus.setText("No drivers are on a ride\nLive tracking stopped");
    }
    else
    {
      JSONObject first = rides.optJSONObject(0);
      StringBuilder copy = new StringBuilder();
      for (int i = 0; i < rides.length(); i++)
      {
        JSONObject ride = rides.optJSONObject(i);
        if (i > 0)
          copy.append("\n\n");
        copy.append(ride.optString("driver_name", "Driver"))
            .append("\nVehicle: ").append(ride.optString("vehicle_number", "—"))
            .append("   Route: ").append(ride.optString("route_name", "Route"))
            .append("\nStatus: LIVE");
      }
      mStatus.setText(copy.toString());
      if (first != null && !first.isNull("latitude") && !first.isNull("longitude"))
      {
        mMarker.setVisibility(View.VISIBLE);
        mMarkerLabel.setVisibility(View.VISIBLE);
        mMarkerLabel.setText(first.optString("driver_name", "Driver"));
        Framework.nativeZoomToPoint(first.optDouble("latitude"), first.optDouble("longitude"), 16, true);
      }
      else
      {
        mMarker.setVisibility(View.GONE);
        mMarkerLabel.setVisibility(View.GONE);
      }
    }
    schedulePoll(3000);
  }

  public void stop()
  {
    mStopped = true;
    mUi.removeCallbacks(mPoll);
    mExecutor.shutdownNow();
    mRoot = null;
  }
}
