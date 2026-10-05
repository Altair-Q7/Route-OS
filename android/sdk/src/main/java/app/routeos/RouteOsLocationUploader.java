package app.routeos;

import android.content.Context;
import android.content.SharedPreferences;
import android.location.Location;
import app.organicmaps.sdk.util.log.Logger;
import java.time.Instant;
import java.util.UUID;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;
import org.json.JSONObject;

/** A single worker persists samples and retries them while the foreground navigation service is alive. */
public final class RouteOsLocationUploader
{
  private static RouteOsLocationUploader sInstance;
  private final Context mContext;
  private final SharedPreferences mPrefs;
  private final RouteOsLocationStore mStore;
  private final ScheduledExecutorService mIo = Executors.newSingleThreadScheduledExecutor();
  private ScheduledFuture<?> mPending;
  private boolean mRunning;
  private long mRetryDelay = 5000;

  private RouteOsLocationUploader(Context context)
  {
    mContext = context.getApplicationContext();
    mPrefs = mContext.getSharedPreferences("routeos", Context.MODE_PRIVATE);
    mStore = new RouteOsLocationStore(mContext, "routeos-locations.db");
  }

  public static synchronized RouteOsLocationUploader get(Context context)
  {
    if (sInstance == null)
      sInstance = new RouteOsLocationUploader(context);
    return sInstance;
  }

  public synchronized void start()
  {
    mRunning = true;
    if (mPending != null)
      mPending.cancel(false);
    mPending = null;
    schedule(0);
  }

  public synchronized void stop()
  {
    mRunning = false;
    if (mPending != null)
      mPending.cancel(false);
    mPending = null;
  }

  private synchronized void schedule(long delay)
  {
    if (mRunning && mPending == null)
      mPending = mIo.schedule(this::drain, delay, TimeUnit.MILLISECONDS);
  }

  public void enqueue(Location location)
  {
    long rideId = mPrefs.getLong("active_ride_id", 0);
    long driverId = mPrefs.getLong("driver_id", 0);
    if (rideId == 0 || driverId == 0)
      return;
    String server = RouteOsApi.baseUrl(mContext);
    Location fix = new Location(location);
    mIo.execute(() -> {
      try
      {
        JSONObject body =
            new JSONObject()
                .put("driver_id", driverId)
                .put("latitude", fix.getLatitude())
                .put("longitude", fix.getLongitude())
                .put("sample_id", UUID.randomUUID().toString())
                .put("recorded_at",
                     Instant.ofEpochMilli(fix.getTime() > 0 ? fix.getTime() : System.currentTimeMillis()).toString());
        if (fix.hasSpeed())
          body.put("speed_mps", Math.max(0, fix.getSpeed()));
        if (fix.hasBearing())
          body.put("bearing", Math.max(0, Math.min(360, fix.getBearing())));
        if (fix.hasAccuracy())
          body.put("accuracy_meters", Math.max(0, fix.getAccuracy()));
        mStore.enqueue(server, driverId, rideId, body);
        if (driverId == mPrefs.getLong("driver_id", 0) && server.equals(RouteOsApi.baseUrl(mContext)))
          mPrefs.edit().putInt("tracking_pending", mStore.count(server, driverId)).apply();
        schedule(0);
      }
      catch (Exception error)
      {
        Logger.w("RouteOsUpload", "Could not persist GPS sample: " + error.getMessage());
        mPrefs.edit().putString("tracking_state", "storage_error").apply();
      }
    });
  }

  private void state(String value, String server, long driverId)
  {
    if (driverId == mPrefs.getLong("driver_id", 0) && server.equals(RouteOsApi.baseUrl(mContext)))
      mPrefs.edit()
          .putString("tracking_state", value)
          .putInt("tracking_pending", mStore.count(server, driverId))
          .apply();
  }

  private void drain()
  {
    synchronized (this)
    {
      mPending = null;
      if (!mRunning)
        return;
    }
    String server = RouteOsApi.baseUrl(mContext);
    long driverId = mPrefs.getLong("driver_id", 0);
    if (driverId == 0)
      return;
    try
    {
      RouteOsLocationStore.Sample sample = mStore.newest(server, driverId);
      if (sample == null)
      {
        long last = mPrefs.getLong("tracking_last_upload", 0);
        state(last == 0                                   ? "waiting_gps"
              : System.currentTimeMillis() - last > 30000 ? "stale"
                                                          : "live",
              server, driverId);
        schedule(5000);
        return;
      }
      try
      {
        RouteOsApi.postForDriver(mContext, server, driverId, "/api/v1/rides/" + sample.rideId() + "/locations",
                                 sample.body());
        mStore.acknowledge(sample.id());
        if (driverId == mPrefs.getLong("driver_id", 0) && server.equals(RouteOsApi.baseUrl(mContext))
            && sample.rideId() == mPrefs.getLong("active_ride_id", 0))
        {
          long recorded = Instant.parse(sample.body().getString("recorded_at")).toEpochMilli();
          mPrefs.edit()
              .putLong("tracking_last_upload", Math.max(recorded, mPrefs.getLong("tracking_last_upload", 0)))
              .apply();
        }
        mRetryDelay = 5000;
        state(System.currentTimeMillis() - mPrefs.getLong("tracking_last_upload", 0) > 30000 ? "stale" : "live", server,
              driverId);
        schedule(0);
      }
      catch (RouteOsApi.ApiException error)
      {
        if (error.status == 401 || error.status == 403)
        {
          state("auth_required", server, driverId);
          schedule(30000);
        }
        else if (error.status == 404 || error.status == 409)
        {
          mStore.discardRide(server, driverId, sample.rideId());
          if (driverId == mPrefs.getLong("driver_id", 0) && server.equals(RouteOsApi.baseUrl(mContext))
              && sample.rideId() == mPrefs.getLong("active_ride_id", 0))
            RouteOsApi.clearActiveRide(mContext);
          schedule(0);
        }
        else if (error.status >= 400 && error.status < 500 && error.status != 408 && error.status != 429)
        {
          mStore.acknowledge(sample.id());
          state("rejected", server, driverId);
          schedule(5000);
        }
        else
          retry(server, driverId);
      }
    }
    catch (Exception error)
    {
      Logger.w("RouteOsUpload", "GPS upload deferred: " + error.getMessage());
      retry(server, driverId);
    }
  }

  private void retry(String server, long driverId)
  {
    state("offline", server, driverId);
    schedule(mRetryDelay);
    mRetryDelay = Math.min(60000, mRetryDelay * 2);
  }
}
