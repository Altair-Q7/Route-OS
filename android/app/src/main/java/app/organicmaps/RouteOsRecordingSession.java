package app.organicmaps;

import android.location.Location;
import androidx.annotation.NonNull;
import java.util.ArrayList;

/** Process-local mirror of the native recording, fed by the foreground GPS service. */
public final class RouteOsRecordingSession {
  private static final ArrayList<Location> POINTS = new ArrayList<>();
  private RouteOsRecordingSession() {}

  public static synchronized void start() { POINTS.clear(); }
  public static synchronized void add(@NonNull Location location) { POINTS.add(new Location(location)); }
  public static synchronized ArrayList<Location> snapshot() { return new ArrayList<>(POINTS); }
  public static synchronized void clear() { POINTS.clear(); }
}
