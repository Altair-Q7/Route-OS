package app.routeos;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertThrows;

import android.content.Context;
import androidx.test.platform.app.InstrumentationRegistry;
import org.junit.After;
import org.junit.Test;

public class RouteOsApiTest
{
  private final Context mContext = InstrumentationRegistry.getInstrumentation().getTargetContext();

  @After
  public void tearDown()
  {
    mContext.getSharedPreferences("routeos", 0).edit().clear().apply();
    RouteOsCredentials.clear(mContext);
  }

  @Test
  public void normalizesUrlsAndRejectsInvalidEndpoints()
  {
    assertEquals("https://example.com/prefix",
                 RouteOsApi.normalizeBaseUrl(mContext, " HTTPS://EXAMPLE.COM/prefix/// "));
    for (String url :
         new String[] {"https://user:pass@example.com", "https://example.com?q=1", "https://example.com#fragment",
                       "https://example.com:70000", "https://example.com:0", "http://example.com",
                       "file:///tmp/backend", "https://bad host"})
      assertThrows(url, IllegalArgumentException.class, () -> RouteOsApi.normalizeBaseUrl(mContext, url));
  }

  @Test
  public void serverSwitchClearsCredentialsAndPreservesOwnedDrafts() throws Exception
  {
    var prefs = mContext.getSharedPreferences("routeos", 0);
    prefs.edit()
        .clear()
        .putString("api_base_url", "https://first.example")
        .putLong("driver_id", 1)
        .putString("planner_draft_1", "old draft")
        .apply();
    RouteOsCredentials.store(mContext, "first-server-token");
    RouteOsApi.setBaseUrl(mContext, "https://second.example/");
    assertEquals("https://second.example", RouteOsApi.baseUrl(mContext));
    assertEquals(0, prefs.getLong("driver_id", 0));
    assertNull(RouteOsCredentials.read(mContext));
    assertEquals("old draft", prefs.getString("planner_draft_https://first.example_1", ""));
  }

  @Test
  public void activeRidePreventsServerSwitchAndLogoutPreservesDrafts()
  {
    var prefs = mContext.getSharedPreferences("routeos", 0);
    prefs.edit()
        .clear()
        .putLong("driver_id", 1)
        .putLong("active_ride_id", 9)
        .putString("planner_draft_owned", "draft")
        .apply();
    assertThrows(IllegalStateException.class, () -> RouteOsApi.setBaseUrl(mContext, "https://other.example"));
    assertEquals(9, prefs.getLong("active_ride_id", 0));
    RouteOsApi.clearActiveRide(mContext);
    RouteOsApi.logout(mContext);
    assertEquals("draft", prefs.getString("planner_draft_owned", ""));
  }
}
