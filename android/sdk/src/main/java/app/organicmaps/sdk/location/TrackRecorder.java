package app.organicmaps.sdk.location;

import androidx.annotation.Keep;
import app.organicmaps.sdk.bookmarks.data.ElevationInfo;
import app.organicmaps.sdk.bookmarks.data.TrackStatistics;

public class TrackRecorder
{
  public static native void nativeStartTrackRecording();

  public static native void nativeStopTrackRecording();

  public static native void nativeSaveTrackRecordingWithName(String name);

  public static native boolean nativeIsTrackRecordingEmpty();

  public static native boolean nativeIsTrackRecordingEnabled();

  /** Complete finalized OM recording: lat, lon, epoch seconds, altitude for each point. */
  public static native double[] nativeRouteOsGetRecordedPoints();

  /** OM's simplification chooses routing anchors; the original GPS recording is unchanged. */
  public static native int[] nativeRouteOsTrackWaypointIndices(double[] latitudeLongitude);

  public static native void nativeSetTrackRecordingStatsListener(TrackRecorder.TrackRecordingUpdateHandler listener);

  public static native ElevationInfo nativeGetElevationInfo();

  public interface TrackRecordingUpdateHandler
  {
    @Keep
    @SuppressWarnings("unused")
    void onTrackRecordingUpdate(TrackStatistics trackStatistics);
  }
}
