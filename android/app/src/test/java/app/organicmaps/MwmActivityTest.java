package app.organicmaps;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import android.content.Intent;
import android.os.Bundle;
import org.junit.Test;

public class MwmActivityTest
{
  @Test
  public void consumedLaunchRestoresRouteOsInsteadOfLeavingABareMap()
  {
    final Intent intent = mock(Intent.class);
    when(intent.getBooleanExtra(MwmActivity.EXTRA_CONSUMED, false)).thenReturn(true);
    assertTrue(MwmActivity.shouldRestoreRouteOs(null, intent));
    when(intent.getBooleanExtra("routeos_native", false)).thenReturn(true);
    assertFalse(MwmActivity.shouldRestoreRouteOs(null, intent));
  }

  @Test
  public void nativeRouteOsScreenRestoresAfterRecreation()
  {
    final Bundle state = mock(Bundle.class);
    when(state.getBoolean("routeos_ui_visible", false)).thenReturn(true);
    assertTrue(MwmActivity.shouldRestoreRouteOs(state, mock(Intent.class)));
    assertFalse(MwmActivity.shouldRestoreRouteOs(null, mock(Intent.class)));
  }

  @Test
  public void unmarkedOrMissingIntentIsNotConsumed()
  {
    assertFalse(MwmActivity.isIntentConsumed(null, null));
    assertFalse(MwmActivity.isIntentConsumed(null, mock(Intent.class)));
  }

  @Test
  public void consumedStateSurvivesCoreRestart()
  {
    final Intent intent = mock(Intent.class);
    when(intent.getBooleanExtra(MwmActivity.EXTRA_CONSUMED, false)).thenReturn(true);

    assertTrue(MwmActivity.isIntentConsumed(null, intent));
  }

  /**
   * The saved state belongs to this very instance, so it is more recent than anything the intent was
   * marked with back when the instance was created.
   */
  @Test
  public void savedStateWinsOverIntent()
  {
    final Bundle savedInstanceState = mock(Bundle.class);
    when(savedInstanceState.getBoolean(MwmActivity.EXTRA_CONSUMED, false)).thenReturn(false);
    final Intent intent = mock(Intent.class);
    when(intent.getBooleanExtra(MwmActivity.EXTRA_CONSUMED, false)).thenReturn(true);

    assertFalse(MwmActivity.isIntentConsumed(savedInstanceState, intent));
  }
}
