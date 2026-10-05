package app.routeos;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;

import android.content.Context;
import androidx.test.platform.app.InstrumentationRegistry;
import org.json.JSONObject;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

public class RouteOsLocationStoreTest
{
  private final Context mContext = InstrumentationRegistry.getInstrumentation().getTargetContext();
  private RouteOsLocationStore mStore;
  private static final String DATABASE = "routeos-outbox-test.db";

  @Before
  public void setUp()
  {
    mContext.deleteDatabase(DATABASE);
    mStore = new RouteOsLocationStore(mContext, DATABASE);
  }

  @After
  public void tearDown()
  {
    mStore.close();
    mContext.deleteDatabase(DATABASE);
  }

  @Test
  public void unacknowledgedSamplesSurviveReopeningAndStayAccountScoped() throws Exception
  {
    mStore.enqueue("https://one.example", 1, 7, new JSONObject().put("sample_id", "older"));
    mStore.enqueue("https://one.example", 1, 7, new JSONObject().put("sample_id", "newest"));
    mStore.enqueue("https://two.example", 2, 8, new JSONObject().put("sample_id", "other"));
    mStore.close();
    mStore = new RouteOsLocationStore(mContext, DATABASE);
    assertNull(mStore.newest("https://two.example", 1));
    var newest = mStore.newest("https://one.example", 1);
    assertEquals("newest", newest.body().getString("sample_id"));
    mStore.acknowledge(newest.id());
    assertEquals("older", mStore.newest("https://one.example", 1).body().getString("sample_id"));
    mStore.discardRide("https://one.example", 1, 7);
    assertNull(mStore.newest("https://one.example", 1));
    assertEquals(1, mStore.count("https://two.example", 2));
  }

  @Test
  public void longOutagesKeepTheNewestBoundedHistory() throws Exception
  {
    for (int i = 0; i <= RouteOsLocationStore.MAX_SAMPLES; ++i)
      mStore.enqueue("https://one.example", 1, 7, new JSONObject().put("number", i));
    assertEquals(RouteOsLocationStore.MAX_SAMPLES, mStore.count("https://one.example", 1));
    assertEquals(RouteOsLocationStore.MAX_SAMPLES, mStore.newest("https://one.example", 1).body().getInt("number"));
  }
}
