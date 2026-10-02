package app.organicmaps.test;

import app.organicmaps.sdk.location.TrackRecorder;
import org.junit.Assert;
import org.junit.Before;
import org.junit.Test;

/** Exercises the real OM JNI simplification on-device, not a mocked platform channel. */
public class RouteOsTrackAnchorsTest
{
  @Before
  public void loadNativeLibrary() { System.loadLibrary("organicmaps"); }

  @Test
  public void shortRecordingKeepsEveryFix()
  {
    Assert.assertArrayEquals(new int[] {0, 1, 2},
        TrackRecorder.nativeRouteOsTrackWaypointIndices(new double[] {10, 77, 10.01, 77.01, 10.02, 77.03}));
  }

  @Test
  public void longRecordingUsesOrderedAnchorsWithoutChangingTheRecording()
  {
    double[] recording = new double[4000];
    for (int i = 0; i < 2000; ++i)
    {
      recording[i * 2] = 10 + i * 0.00001;
      recording[i * 2 + 1] = 77 + Math.sin(i / 15.0) * 0.002;
    }
    double[] original = recording.clone();
    int[] anchors = TrackRecorder.nativeRouteOsTrackWaypointIndices(recording);
    Assert.assertTrue(anchors.length >= 2 && anchors.length <= 101);
    Assert.assertEquals(0, anchors[0]);
    Assert.assertEquals(1999, anchors[anchors.length - 1]);
    for (int i = 1; i < anchors.length; ++i) Assert.assertTrue(anchors[i] > anchors[i - 1]);
    Assert.assertArrayEquals(original, recording, 0);
  }
}
