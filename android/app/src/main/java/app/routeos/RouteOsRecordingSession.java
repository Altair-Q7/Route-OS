package app.routeos;

import android.location.Location;
import androidx.annotation.NonNull;
import java.util.ArrayList;

/** Process-local mirror of the native recording, fed by the foreground GPS service. */
public final class RouteOsRecordingSession {
  private static final ArrayList<Location> POINTS = new ArrayList<>();
  private static boolean active;
  private RouteOsRecordingSession() {}

  public static synchronized void start() { POINTS.clear(); active = true; }

  public static synchronized boolean isActive() { return active; }

  /**
   * Mirrors the native recorder's location stream for the RouteOS upload. The foreground activity
   * and TrackRecordingService can both receive the same fix, so identical adjacent fixes are
   * ignored without dropping distinct intermediate GPS samples.
   */
  public static synchronized void add(@NonNull Location location) {
    if (!active)
      return;
    if (!POINTS.isEmpty()) {
      Location previous = POINTS.get(POINTS.size() - 1);
      boolean sameCoordinates = previous.getLatitude() == location.getLatitude()
          && previous.getLongitude() == location.getLongitude();
      boolean sameTimestamp = previous.getTime() == location.getTime();
      if (sameCoordinates && (sameTimestamp || location.getTime() == 0 || previous.getTime() == 0))
        return;
    }
    POINTS.add(new Location(location));
  }

  public static synchronized ArrayList<Location> snapshot() { return new ArrayList<>(POINTS); }

  /** Stops accepting late service callbacks and returns the complete captured sequence. */
  public static synchronized ArrayList<Location> finish() {
    active = false;
    return new ArrayList<>(POINTS);
  }

  public static synchronized void clear() { active = false; POINTS.clear(); }
}
