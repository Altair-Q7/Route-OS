package app.routeos.bridge;

import android.content.Context;
import android.content.SharedPreferences;
import android.location.Location;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.widget.FrameLayout;
import app.organicmaps.MwmActivity;
import app.organicmaps.MwmApplication;
import app.organicmaps.sdk.Framework;
import app.organicmaps.sdk.MapView;
import app.organicmaps.sdk.Router;
import app.organicmaps.sdk.bookmarks.data.BookmarkManager;
import app.organicmaps.sdk.location.LocationState;
import app.organicmaps.sdk.routing.*;
import app.organicmaps.sdk.search.*;
import app.routeos.RouteOsApi;
import app.routeos.RouteOsDraftStore;
import app.routeos.RouteOsTrackPreview;
import io.flutter.embedding.android.FlutterSurfaceView;
import io.flutter.embedding.android.FlutterView;
import io.flutter.embedding.engine.FlutterEngine;
import io.flutter.embedding.engine.dart.DartExecutor;
import io.flutter.plugin.common.*;
import io.flutter.plugin.platform.*;
import java.util.*;
import java.util.concurrent.*;
import org.json.*;

/** One Flutter engine and one existing OM map, owned by MwmActivity's lifecycle. */
public final class RouteOsFlutterHost implements SearchListener, BookmarkManager.BookmarksLoadingListener {
  private final MwmActivity activity;
  private final FlutterEngine engine;
  private final FlutterView view;
  private final MethodChannel methods;
  private EventChannel.EventSink sink;
  private final ExecutorService io = Executors.newSingleThreadExecutor();
  private volatile boolean closed;
  private long searchStamp;
  private Runnable pendingCalculation;
  private boolean calculating;
  private long calculationGeneration;
  private boolean selectedPoint;
  private boolean arrivalSent;
  private long restoringRideId;
  private MethodChannel.Result pendingRideResult;
  private JSONObject pendingRideData;
  private long previewGeneration;
  private long recordedPreviewId;
  private final SharedPreferences.OnSharedPreferenceChangeListener trackingListener = this::trackingChanged;
  private void trackingChanged(SharedPreferences prefs, String key)
  {
    if ("tracking_state".equals(key) || "tracking_pending".equals(key))
      emitTrackingStatus();
    if ("active_ride_id".equals(key) && prefs.getLong("active_ride_id", 0) == 0 && !closed)
      activity.runOnUiThread(() -> {
        if (!closed)
          activity.routeOsFlutterFinishRide();
      });
  }
  private final Runnable rideBuildTimeout = () -> {
    if (pendingRideResult != null) {
      routeFailed("Navigation build timed out. Check offline map coverage and retry.", -1);
      RoutingController.get().cancel();
    }
  };
  private final android.os.Handler handler = new android.os.Handler(android.os.Looper.getMainLooper());

  public RouteOsFlutterHost(MwmActivity activity, MapView map) {
    this.activity = activity;
    engine = new FlutterEngine(activity);
    engine.getPlatformViewsControllerDelegator().attach(activity, engine.getRenderer(), engine.getDartExecutor());
    engine.getPlatformViewsController().getRegistry().registerViewFactory("routeos/map", new PlatformViewFactory(StandardMessageCodec.INSTANCE) {
      @Override public PlatformView create(Context context, int id, Object args) {
        android.util.Log.i("RouteOsMap", "Embedding native map " + id);
        if (map.getParent() instanceof ViewGroup parent) parent.removeView(map);
        FrameLayout wrapper = new FrameLayout(activity);
        wrapper.addView(map, new FrameLayout.LayoutParams(-1, -1));
        final float[] down = new float[2];
        final long[] time = new long[1];
        map.setOnTouchListener((v, e) -> {
          if (e.getActionMasked() == MotionEvent.ACTION_DOWN) { selectedPoint=false; down[0] = e.getX(); down[1] = e.getY(); time[0] = e.getEventTime(); }
          if (e.getActionMasked() == MotionEvent.ACTION_UP && e.getPointerCount() == 1 && e.getEventTime() - time[0] < 500 && Math.hypot(e.getX()-down[0], e.getY()-down[1]) < 20) {
            double[] p = Framework.nativeRouteOsPixelToLatLon(e.getX(), e.getY());
            handler.postDelayed(() -> { if(!selectedPoint) emit("map.tap", java.util.Map.of("latitude", p[0], "longitude", p[1])); },150);
          }
          return false;
        });
        return new PlatformView() {
          public View getView() { return wrapper; }
          public void dispose() { map.setOnTouchListener(null); wrapper.removeView(map); }
        };
      }
    });
    methods = new MethodChannel(engine.getDartExecutor().getBinaryMessenger(), "routeos/v1/methods");
    methods.setMethodCallHandler(this::command);
    new EventChannel(engine.getDartExecutor().getBinaryMessenger(), "routeos/v1/events")
        .setStreamHandler(new EventChannel.StreamHandler() {
          public void onListen(Object args, EventChannel.EventSink value)
          {
            sink = value;
            emitTrackingStatus();
          }
          public void onCancel(Object args)
          {
            sink = null;
          }
        });
    SearchEngine.INSTANCE.addListener(this);
    BookmarkManager.INSTANCE.addLoadingListener(this);
    activity.getSharedPreferences("routeos", 0).registerOnSharedPreferenceChangeListener(trackingListener);
    view = new FlutterView(activity, new FlutterSurfaceView(activity));
    view.attachToFlutterEngine(engine);
    engine.getDartExecutor().executeDartEntrypoint(DartExecutor.DartEntrypoint.createDefault());
    engine.getLifecycleChannel().appIsResumed();
    // The initial Organic Maps bookmark load can finish before this host registers as a
    // listener. Reconcile once more after that load without disturbing a preview selected by
    // the user in the meantime.
    handler.postDelayed(() -> {
      if (closed || activity.getSharedPreferences("routeos", 0).getLong("active_ride_id", 0) != 0)
        return;
      if (recordedPreviewId > 0)
        RouteOsTrackPreview.retainImported(activity, recordedPreviewId);
      else
        RouteOsTrackPreview.clear(activity);
    }, 1000);
  }

  public View getView() { return view; }
  public void back() { if (!closed) engine.getNavigationChannel().popRoute(); }
  public void pointSelected(RoutePointInfo point) {
    selectedPoint=true;
    emit("map.point.selected", java.util.Map.of("index", point.mMarkType==RouteMarkType.Start?0:point.mMarkType==RouteMarkType.Finish?-1:point.mIntermediateIndex+1));
  }
  public void resume() { if (!closed) engine.getLifecycleChannel().appIsResumed(); }
  public void pause() { if (!closed) engine.getLifecycleChannel().appIsInactive(); }
  public void destroy() {
    closed = true; sink = null; handler.removeCallbacksAndMessages(null);
    SearchEngine.INSTANCE.removeListener(this); io.shutdownNow(); methods.setMethodCallHandler(null);
    BookmarkManager.INSTANCE.removeLoadingListener(this);
    activity.getSharedPreferences("routeos", 0).unregisterOnSharedPreferenceChangeListener(trackingListener);
    view.detachFromFlutterEngine(); engine.getPlatformViewsController().detach(); engine.getPlatformViewsController2().detach(); engine.destroy();
  }
  public void emit(String type, Object data) {
    activity.runOnUiThread(() -> { if (!closed && sink != null) sink.success(java.util.Map.of("version", 1, "type", type, "data", data)); });
  }
  private void emitTrackingStatus()
  {
    var prefs = activity.getSharedPreferences("routeos", 0);
    String state = prefs.getString("tracking_state", "waiting_gps");
    int label = switch (state)
    {
      case "live" -> app.organicmaps.R.string.routeos_tracking_live;
      case "stale" -> app.organicmaps.R.string.routeos_tracking_stale;
      case "offline" -> app.organicmaps.R.string.routeos_tracking_offline;
      case "auth_required" -> app.organicmaps.R.string.routeos_tracking_auth_required;
      case "storage_error" -> app.organicmaps.R.string.routeos_tracking_storage_error;
      case "rejected" -> app.organicmaps.R.string.routeos_tracking_rejected;
      default -> app.organicmaps.R.string.routeos_tracking_waiting_gps;
    };
    emit("tracking.status", java.util.Map.of("state", state, "message", activity.getString(label), "pending",
                                             prefs.getInt("tracking_pending", 0)));
  }
  public void routeReady() {
    if (!calculating)
      return;
    RoutingInfo info = Framework.nativeGetRouteFollowingInfo();
    if (info == null) { routeFailed("Routing returned no summary. Try again.", -1); return; }
    if ((pendingRideResult != null || restoringRideId > 0) && !Framework.nativeIsRouteBuilt()) {
      routeFailed("Navigation could not be built. Check regional map coverage and retry.", -1);
      return;
    }
    calculating = false;
    if (pendingRideResult != null) {
      MethodChannel.Result result = pendingRideResult;
      JSONObject data = pendingRideData;
      pendingRideResult = null; pendingRideData = null;
      handler.removeCallbacks(rideBuildTimeout);
      async(result, () -> {
        JSONObject ride = RouteOsApi.startRide(activity,data.getLong("id"),data.getString("vehicle_type"),data.getString("vehicle_number"));
        activity.runOnUiThread(() -> { if (!closed) {
          activity.routeOsFlutterStartRide(ride.optLong("id"));
          navigationStarted(ride.optLong("id"));
        }});
        return ride;
      });
      return;
    }
    if (restoringRideId == 0) Framework.nativeRouteOsShowRouteOverview();
    emit("route.ready", java.util.Map.of("generation", calculationGeneration, "distance_meters",
                                         meters(info.distToTarget), "duration_seconds", info.totalTimeInSeconds));
    if(restoringRideId>0){
      long rideId=restoringRideId;restoringRideId=0;
      if(activity.getSharedPreferences("routeos",0).getLong("active_ride_id",0)==rideId){
        activity.routeOsFlutterStartRide(rideId);navigationStarted(rideId);
      }
    }
  }
  public void rideStopped() {
    recordedPreviewId = 0; previewGeneration++; RouteOsTrackPreview.clear(activity);
    arrivalSent = false;
    restoringRideId = 0;
    calculating = false;
    if (pendingCalculation != null) handler.removeCallbacks(pendingCalculation);
    pendingCalculation = null;
  }
  private void navigationStarted(long rideId) {
    RoutingInfo info=RoutingController.get().getCachedRoutingInfo();
    if(info==null){emit("navigation.started",java.util.Map.of("id",rideId,"maneuver","Waiting for GPS guidance"));return;}
    emit("navigation.started",java.util.Map.of("id",rideId,"maneuver",info.carDirection.name(),
      "street",info.nextStreet==null?"":info.nextStreet,"turn_distance",Math.max(0,meters(info.distToTurn)),
      "distance_meters",Math.max(0,meters(info.distToTarget)),"duration_seconds",Math.max(0,info.totalTimeInSeconds)));
  }
  public void routeFailed(String message, int code) {
    if (!calculating && pendingRideResult == null && restoringRideId == 0)
      return;
    calculating = false;
    restoringRideId = 0;
    handler.removeCallbacks(rideBuildTimeout);
    if (pendingRideResult != null) pendingRideResult.error("ROUTE_FAILED", message, null);
    pendingRideResult = null; pendingRideData = null;
    emit("route.failed", java.util.Map.of("generation", calculationGeneration, "message", message, "code", code));
  }
  private static double meters(app.organicmaps.sdk.util.Distance distance) {
    return distance.mDistance * switch(distance.mUnits) {
      case Meters -> 1; case Kilometers -> 1000; case Feet -> 0.3048; case Miles -> 1609.344;
    };
  }
  public void progress(Location location, RoutingInfo info) {
    if (info == null || activity.getSharedPreferences("routeos",0).getLong("active_ride_id",0)==0) return;
    double distanceMeters=Math.max(0,meters(info.distToTarget));
    boolean arrived=Framework.nativeIsRouteFinished() && distanceMeters <= 5;
    if(arrived && !arrivalSent){arrivalSent=true;emit("navigation.arrived",java.util.Map.of());}
    emit("navigation.progress", java.util.Map.of("maneuver", info.carDirection.name(), "street", info.nextStreet == null ? "" : info.nextStreet,
      "turn_distance", Math.max(0, meters(info.distToTurn)), "distance_meters", distanceMeters, "duration_seconds", info.totalTimeInSeconds,
      "speed", location.hasSpeed() ? location.getSpeed()*3.6 : 0, "speed_limit", info.speedLimitMps>0?info.speedLimitMps*3.6:-1, "arrived", arrived));
  }

  private void async(MethodChannel.Result result, Callable<Object> task) {
    if (closed) { result.error("CLOSED", "Screen closed", null); return; }
    try { io.execute(() -> {
      try { Object value = plain(task.call()); activity.runOnUiThread(() -> { if (!closed) result.success(value); }); }
      catch (Exception error) { activity.runOnUiThread(() -> { if (!closed) result.error(error instanceof RouteOsApi.ApiException api && api.status==401?"AUTH_EXPIRED":"REQUEST_FAILED", error.getMessage(), null); }); }
    }); } catch (RejectedExecutionException stopped) {
      result.error("CLOSED", "Screen closed", null);
    }
  }

  private void loadRoutes(MethodChannel.Result result) {
    if (closed) { result.error("CLOSED", "Screen closed", null); return; }
    try { io.execute(() -> {
      try {
        JSONArray routes = RouteOsApi.getRoutes(activity);
        activity.runOnUiThread(() -> {
          if (closed) return;
          RouteOsTrackPreview.clearLegacyRecordedTracks(activity, routes);
          try { result.success(plain(routes)); }
          catch (Exception error) { result.error("REQUEST_FAILED", error.getMessage(), null); }
        });
      } catch (Exception error) {
        activity.runOnUiThread(() -> { if (!closed) result.error(
            error instanceof RouteOsApi.ApiException api && api.status == 401 ? "AUTH_EXPIRED" : "REQUEST_FAILED",
            error.getMessage(), null); });
      }
    }); } catch (RejectedExecutionException stopped) {
      result.error("CLOSED", "Screen closed", null);
    }
  }

  private void command(MethodCall call, MethodChannel.Result result) {
    try {
      java.util.Map<?,?> envelope = (java.util.Map<?,?>)call.arguments;
      if (!(envelope.get("version") instanceof Number n) || n.intValue() != 1) { result.error("UNSUPPORTED_VERSION", "Bridge version must be 1", null); return; }
      JSONObject data = new JSONObject((java.util.Map<?,?>)envelope.get("data"));
      switch (call.method) {
        case "diagnostic" -> { android.util.Log.w("RouteOsMap", data.optString("message")); result.success(null); }
        case "close" -> { activity.finish(); result.success(null); }
        case "session" -> {
          var prefs = activity.getSharedPreferences("routeos", Context.MODE_PRIVATE);
          result.success(java.util.Map.of(
              "id", prefs.getLong("driver_id", 0), "name", prefs.getString("driver_name", ""), "role",
              prefs.getString("role", "driver"), "development",
              (activity.getApplicationInfo().flags & android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0,
              "active_ride_id", prefs.getLong("active_ride_id", 0), "recording",
              app.organicmaps.sdk.location.TrackRecorder.nativeIsTrackRecordingEnabled(), "tracking_stale_label",
              activity.getString(app.organicmaps.R.string.routeos_tracking_stale)));
        }
        case "login" -> async(result, () -> RouteOsApi.login(activity, data.getString("name"), data.optString("password", null)));
        case "server" ->
        {
          if (app.organicmaps.sdk.location.TrackRecorder.nativeIsTrackRecordingEnabled())
            throw new IllegalStateException("Stop recording before changing servers");
          RouteOsApi.setBaseUrl(activity, data.getString("url"));
          result.success(null);
        }
        case "maps.download" -> { activity.startActivity(new android.content.Intent(activity, app.organicmaps.downloader.DownloaderActivity.class)); result.success(null); }
        case "routes" -> loadRoutes(result);
        case "route" -> {
          long generation=++previewGeneration;
          recordedPreviewId=0; RouteOsTrackPreview.clear(activity);
          async(result, () -> {
            JSONObject route=RouteOsApi.getRoute(activity,data.getLong("id"));
            if("recorded".equals(route.optString("route_type"))) importRecording(route,generation);
            return route;
          });
        }
        case "delete" -> async(result, () -> RouteOsApi.deleteRoute(activity, data.getLong("id")));
        case "rename" -> async(result, () -> RouteOsApi.renameRoute(activity, data.getLong("id"), data.getString("name")));
        case "favorite" -> async(result, () -> RouteOsApi.setFavorite(activity, data.getLong("id"), data.getBoolean("favorite")));
        case "recent.clear" -> async(result, () -> RouteOsApi.clearRecent(activity, data.getLong("id")));
        case "share" -> async(result, () -> RouteOsApi.shareRoute(activity, data.getLong("id"), data.optLong("recipient_id",0)));
        case "save" -> async(result, () -> RouteOsApi.post(activity, "/api/v1/planned-routes", data));
        case "draft.save" ->
        {
          RouteOsDraftStore.save(activity.getSharedPreferences("routeos", 0), data.toString());
          result.success(null);
        }
        case "draft.load" ->
        {
          result.success(plain(new JSONObject(RouteOsDraftStore.load(activity.getSharedPreferences("routeos", 0)))));
        }
        case "logout" -> {
          if (activity.getSharedPreferences("routeos",0).getLong("active_ride_id",0) != 0 || app.organicmaps.sdk.location.TrackRecorder.nativeIsTrackRecordingEnabled()) throw new IllegalStateException("End the ride/recording before switching accounts");
          async(result, () -> {
            try
            {
              RouteOsApi.post(activity, "/api/v1/auth/logout", new JSONObject());
            }
            catch (RouteOsApi.ApiException expired)
            {
              if (expired.status != 401)
                throw expired;
            }
            RouteOsApi.logout(activity);
            activity.runOnUiThread(() -> { if (!closed) {
              recordedPreviewId=0; previewGeneration++;
              Framework.nativeClearApiPoints(); RoutingController.get().cancel(); RouteOsTrackPreview.clear(activity);
            }});
            return null;
          });
        }
        case "location" -> {
          Location loc = MwmApplication.from(activity).getLocationHelper().getSavedLocation();
          if (loc == null) throw new IllegalStateException("Waiting for GPS. Enable location and try again.");
          Framework.nativeZoomToPoint(loc.getLatitude(),loc.getLongitude(),15,true);
          result.success(java.util.Map.of("latitude",loc.getLatitude(),"longitude",loc.getLongitude()));
        }
        case "zoom" -> { if (data.optBoolean("in")) app.organicmaps.sdk.Map.zoomIn(); else app.organicmaps.sdk.Map.zoomOut(); result.success(null); }
        case "center" -> { Framework.nativeZoomToPoint(data.getDouble("latitude"),data.getDouble("longitude"),15,true); result.success(null); }
        case "preview.clear" -> {
          recordedPreviewId=0; previewGeneration++; RouteOsTrackPreview.clear(activity);
          if(activity.getSharedPreferences("routeos",0).getLong("active_ride_id",0)!=0) throw new IllegalStateException("Ride is still live");
          calculating=false;
          if(pendingCalculation!=null)handler.removeCallbacks(pendingCalculation);
          RoutingController.get().cancel();
          Framework.nativeCloseRouting();
          Framework.nativeRemoveRoute();
          Framework.nativeRemoveRoutePoints();
          Framework.nativeClearApiPoints();
          result.success(null);
        }
        case "calculate" -> {
          if (RoutingController.get().isNavigating() || pendingRideResult != null)
            throw new IllegalStateException("End navigation before editing a route");
          calculating = false;
          if (pendingCalculation != null) handler.removeCallbacks(pendingCalculation);
          RoutingController.get().cancel();
          pendingCalculation = () ->
          {
            if (!closed)
              try
              {
                calculate(data);
              }
              catch (Exception failure)
              {
                emit("route.failed",
                     java.util.Map.of("generation", data.optLong("generation", 0), "message", failure.getMessage()));
              }
          };
          handler.postDelayed(pendingCalculation, 250); result.success(null);
        }
        case "search" -> {
          searchStamp = System.nanoTime();
          String query=data.getString("query").trim();
          if(query.isEmpty()){emit("search.results",java.util.List.of());emit("search.finished",java.util.Map.of());}
          else SearchEngine.INSTANCE.search(activity,query,false,searchStamp,false,0,0);
          result.success(null);
        }
        case "ride.start" -> {
          startRideCommand(data, result);
        }
        case "ride.restore" ->
          async(result, () -> {
            JSONObject ride;
            try
            {
              ride = RouteOsApi.getOwnActiveRide(activity);
            }
            catch (RouteOsApi.ApiException missingRide)
            {
              if (missingRide.status != 404)
                throw missingRide;
              RouteOsApi.clearActiveRide(activity);
              return null;
            }
            activity.getSharedPreferences("routeos", 0).edit().putLong("active_ride_id", ride.getLong("id")).apply();
            if (!RoutingController.get().isNavigating())
            {
              JSONObject route = RouteOsApi.getRoute(activity, ride.getLong("route_id"));
              activity.runOnUiThread(() -> {
                if (!closed)
                  try
                  {
                    restoringRideId = ride.getLong("id");
                    RouteMarkData[] saved = Framework.nativeGetRoutePoints();
                    JSONArray points = saved.length >= 2 && saved[0].mIsMyPosition ? nativeRoutePoints()
                                                                                   : route.getJSONArray("points");
                    JSONObject definition = "recorded".equals(route.optString("route_type"))
                                              ? recordedNavigationDefinition(route)
                                              : navigationDefinition(points);
                    calculate(definition);
                  }
                  catch (Exception failure)
                  {
                    routeFailed(failure.getMessage(), -1);
                  }
              });
            }
            return ride;
          });
        case "ride.end" ->
          async(result, () -> {
            RouteOsApi.endRide(activity, activity.getSharedPreferences("routeos", 0).getLong("active_ride_id", 0));
            return java.util.Map.of("ended", true);
          });
        case "active" -> async(result, () -> RouteOsApi.getActiveRides(activity));
        case "admin.points" -> {
          if (!"admin".equals(activity.getSharedPreferences("routeos",0).getString("role","driver"))) throw new IllegalStateException("Admin only");
          JSONArray rides=data.getJSONArray("rides"); StringBuilder url=new StringBuilder("om://map?");
          int locations=0;
          for(int i=0;i<rides.length();i++) { JSONObject ride=rides.getJSONObject(i); if(ride.isNull("latitude")||ride.isNull("longitude"))continue;
            if(locations++>0)url.append('&');url.append("ll=").append(ride.getDouble("latitude")).append(',').append(ride.getDouble("longitude")).append("&n=").append(android.net.Uri.encode(ride.optString("driver_name")));
          }
          Framework.nativeClearApiPoints();
          if(locations>0){Framework.nativeParseAndSetApiUrl(url.toString());app.organicmaps.sdk.Map.executeMapApiRequest();}
          result.success(null);
        }
        case "record" -> { activity.routeOsFlutterRecord(); result.success(null); }
        case "record.stop" -> { activity.onTrackRecordingSaved(); result.success(null); }
        case "record.cancel" -> { activity.routeOsFlutterCancelRecording(); result.success(null); }
        default -> result.error("UNSUPPORTED_COMMAND",call.method,null);
      }
    } catch (Exception error) { result.error("INVALID_COMMAND",error.getMessage(),null); }
  }

  private void calculate(JSONObject data) throws Exception {
    if (!"car".equals(data.optString("profile", "car"))) throw new IllegalArgumentException("This build supports the car routing profile");
    if (RoutingController.get().isNavigating()) throw new IllegalStateException("End navigation before editing a route");
    JSONArray points = data.getJSONArray("points");
    if (points.length()>102) throw new IllegalArgumentException("Organic Maps supports at most 102 route points");
    RoutingController controller = RoutingController.get();
    calculating = false;
    controller.cancel(); Framework.nativeRemoveRoutePoints();
    calculationGeneration = data.optLong("generation", 0);
    controller.prepare(null,null,Router.Vehicle);
    for (int i=0;i<points.length();i++) {
      JSONObject p=points.getJSONObject(i);
      RouteMarkType type = i==0 ? RouteMarkType.Start : i==points.length()-1 ? RouteMarkType.Finish : RouteMarkType.Intermediate;
      Framework.addRoutePoint(new RouteMarkData(p.optString("label","Point "+(i+1)),"",type,Math.max(0,i-1),true,i==0 && data.optBoolean("navigation",false),false,p.getDouble("latitude"),p.getDouble("longitude")),false);
    }
    if (points.length()>=2) { calculating = true; emit("route.calculating",java.util.Map.of()); controller.checkAndBuildRoute(); }
  }
  private void startRideCommand(JSONObject data, MethodChannel.Result result) {
    try {
      io.execute(() -> {
        try {
          JSONObject route = RouteOsApi.getRoute(activity, data.getLong("id"));
          activity.runOnUiThread(() -> {
            if (closed) return;
            try {
              boolean recorded = "recorded".equals(route.optString("route_type"));
              // Recorded routes bypass the Flutter planner, so discard any stale planner
              // calculation before building navigation for the recorded destination.
              if (recorded) {
                calculating = false;
                if (pendingCalculation != null) {
                  handler.removeCallbacks(pendingCalculation);
                  pendingCalculation = null;
                }
                RoutingController.get().cancel();
                Framework.nativeRemoveRoutePoints();
              } else if (calculating) {
                throw new IllegalStateException("Route calculation is still in progress");
              }
              JSONObject definition = recorded
                  ? recordedNavigationDefinition(route)
                  : navigationDefinition(nativeRoutePoints());
              pendingRideResult = result; pendingRideData = data;
              handler.postDelayed(rideBuildTimeout, 60_000);
              calculate(definition);
            } catch (Exception failure) {
              pendingRideResult = null;
              pendingRideData = null;
              calculating = false;
              handler.removeCallbacks(rideBuildTimeout);
              result.error("INVALID_COMMAND", failure.getMessage(), null);
            }
          });
        } catch (Exception error) {
          activity.runOnUiThread(() -> {
            if (!closed)
              result.error(
                  error instanceof RouteOsApi.ApiException api && api.status == 401 ? "AUTH_EXPIRED" : "REQUEST_FAILED",
                  error.getMessage(), null);
          });
        }
      });
    } catch (RejectedExecutionException stopped) {
      result.error("CLOSED", "Screen closed", null);
    }
  }
  private JSONArray nativeRoutePoints() throws JSONException {
    JSONArray points=new JSONArray();
    for(RouteMarkData p:Framework.nativeGetRoutePoints()) {
      if(p.mIsPassed || (p.mPointType==RouteMarkType.Start && p.mIsMyPosition)) continue;
      points.put(new JSONObject().put("latitude",p.mLat).put("longitude",p.mLon).put("label",p.mTitle==null?"":p.mTitle));
    }
    return points;
  }
  private JSONObject recordedNavigationDefinition(JSONObject route) throws Exception {
    JSONArray recording=route.getJSONArray("points");
    if(recording.length()==0) throw new IllegalStateException("The recorded route has no destination");
    return navigationDefinition(new JSONArray().put(recording.getJSONObject(recording.length()-1)));
  }
  private void importRecording(JSONObject route,long generation) throws Exception {
    JSONArray fixes=route.getJSONArray("points"),coordinates=new JSONArray();
    for(int i=0;i<fixes.length();i++) {
      JSONObject fix=fixes.getJSONObject(i);
      coordinates.put(new JSONArray().put(fix.getDouble("longitude")).put(fix.getDouble("latitude")));
    }
    long routeId=route.getLong("id");
    java.io.File file=new java.io.File(activity.getCacheDir(),"routeos-route-"+routeId+".track-"+System.nanoTime()+".geojson");
    JSONObject feature=new JSONObject().put("type","Feature").put("properties",new JSONObject().put("name","routeos-route-"+routeId))
      .put("geometry",new JSONObject().put("type","LineString").put("coordinates",coordinates));
    JSONObject collection=new JSONObject().put("type","FeatureCollection").put("features",new JSONArray().put(feature));
    try(java.io.FileOutputStream output=new java.io.FileOutputStream(file)) {
      output.write(collection.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));
    }
    activity.runOnUiThread(()->{
      if(closed || generation!=previewGeneration){file.delete();return;}
      recordedPreviewId=routeId; RouteOsTrackPreview.replace(activity,file,routeId);
    });
  }
  @Override public void onBookmarksLoadingFinished() {
    if(closed) return;
    if(recordedPreviewId>0) RouteOsTrackPreview.retainImported(activity,recordedPreviewId);
    else RouteOsTrackPreview.clear(activity);
  }
  private JSONObject navigationDefinition(JSONArray points) throws Exception {
    Location location=MwmApplication.from(activity).getLocationHelper().getSavedLocation();
    if(location==null) throw new IllegalStateException("Wait for a GPS fix before starting navigation");
    if(points.length()==0) throw new IllegalStateException("The route has no remaining destination");
    JSONArray navigation=new JSONArray();
    navigation.put(new JSONObject().put("latitude",location.getLatitude()).put("longitude",location.getLongitude()).put("label","Current location"));
    for(int i=0;i<points.length();i++) {
      JSONObject point=points.getJSONObject(i);
      float[] distance=new float[1];
      Location.distanceBetween(location.getLatitude(),location.getLongitude(),point.getDouble("latitude"),point.getDouble("longitude"),distance);
      if(i==0 && points.length()>1 && distance[0]<20) continue;
      navigation.put(point);
    }
    if(navigation.length()>102) throw new IllegalStateException("Navigation needs one point for current GPS. Remove a waypoint or move to the saved start first.");
    return new JSONObject().put("points",navigation).put("profile","car").put("navigation",true);
  }
  @Override public void onResultsUpdate(SearchResult[] results,long timestamp) {
    if (closed || timestamp!=searchStamp) return;
    List<Object> rows=new ArrayList<>();
    for (SearchResult r:results) if(r.type!=SearchResult.TYPE_PURE_SUGGEST) rows.add(java.util.Map.of("label",r.name,"address",r.description==null?"":r.description.region,"latitude",r.lat,"longitude",r.lon));
    emit("search.results",rows);
  }
  @Override public void onResultsEnd(long timestamp) {
    if (!closed && timestamp==searchStamp) emit("search.finished",java.util.Map.of());
  }
  static Object plain(Object value) throws JSONException {
    if (value==JSONObject.NULL) return null;
    if (value instanceof JSONObject o) { java.util.Map<String,Object> m=new HashMap<>(); Iterator<String> keys=o.keys(); while(keys.hasNext()) { String k=keys.next(); m.put(k,plain(o.get(k))); } return m; }
    if (value instanceof JSONArray a) { List<Object> l=new ArrayList<>(); for(int i=0;i<a.length();i++) l.add(plain(a.get(i))); return l; }
    return value;
  }
}
