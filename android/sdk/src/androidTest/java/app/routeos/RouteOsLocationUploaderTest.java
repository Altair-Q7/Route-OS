package app.routeos;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;

import android.content.Context;
import android.location.Location;
import androidx.test.platform.app.InstrumentationRegistry;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import org.json.JSONObject;
import org.junit.After;
import org.junit.Test;

public class RouteOsLocationUploaderTest
{
  private final Context mContext = InstrumentationRegistry.getInstrumentation().getTargetContext();
  private final List<JSONObject> mRequests = Collections.synchronizedList(new ArrayList<>());
  private ServerSocket mServer;
  private Thread mServerThread;
  private RouteOsLocationUploader mUploader;

  private void start(int... responses) throws Exception
  {
    var prefs = mContext.getSharedPreferences("routeos", 0);
    prefs.edit().clear().apply();
    mServer = new ServerSocket(0, 2, InetAddress.getByName("127.0.0.1"));
    String server = "http://127.0.0.1:" + mServer.getLocalPort();
    RouteOsApi.setBaseUrl(mContext, server);
    prefs.edit().putLong("driver_id", 987).putLong("active_ride_id", 765).apply();
    mServerThread = new Thread(() -> {
      try
      {
        for (int status : responses)
        {
          try (var socket = mServer.accept())
          {
            var reader = new BufferedReader(new InputStreamReader(socket.getInputStream(), StandardCharsets.UTF_8));
            reader.readLine();
            int length = 0;
            for (String line = reader.readLine(); line != null && !line.isEmpty(); line = reader.readLine())
              if (line.toLowerCase(java.util.Locale.ROOT).startsWith("content-length:"))
                length = Integer.parseInt(line.substring(line.indexOf(':') + 1).trim());
            char[] body = new char[length];
            for (int read = 0; read < length;)
            {
              int count = reader.read(body, read, length - read);
              if (count < 0)
                throw new java.io.IOException("Incomplete request");
              read += count;
            }
            mRequests.add(new JSONObject(new String(body)));
            String response = "{\"id\":1,\"detail\":\"test response\"}";
            String header = "HTTP/1.1 " + status + " Test\r\nContent-Type: application/json\r\nContent-Length: "
                          + response.length() + "\r\nConnection: close\r\n\r\n";
            socket.getOutputStream().write((header + response).getBytes(StandardCharsets.UTF_8));
          }
        }
      }
      catch (Exception error)
      {
        if (!mServer.isClosed())
          throw new AssertionError(error);
      }
    });
    mServerThread.start();
    mUploader = RouteOsLocationUploader.get(mContext);
    mUploader.start();
    Location fix = new Location("test");
    fix.setLatitude(10);
    fix.setLongitude(77);
    fix.setTime(System.currentTimeMillis());
    mUploader.enqueue(fix);
  }

  private void awaitState(String state) throws Exception
  {
    var prefs = mContext.getSharedPreferences("routeos", 0);
    long deadline = System.nanoTime() + java.util.concurrent.TimeUnit.SECONDS.toNanos(20);
    while (!state.equals(prefs.getString("tracking_state", "")) && System.nanoTime() < deadline)
      Thread.sleep(50);
    assertEquals(state, prefs.getString("tracking_state", ""));
  }

  @After
  public void tearDown() throws Exception
  {
    if (mUploader != null)
      mUploader.stop();
    if (mServer != null)
      mServer.close();
    if (mServerThread != null)
      mServerThread.join(2000);
    try (var store = new RouteOsLocationStore(mContext, "routeos-locations.db"))
    {
      store.discardRide(RouteOsApi.baseUrl(mContext), 987, 765);
    }
    mContext.getSharedPreferences("routeos", 0).edit().clear().apply();
  }

  @Test
  public void temporaryServerFailureRetainsAndRetriesTheSameSample() throws Exception
  {
    start(500, 201);
    awaitState("offline");
    try (var store = new RouteOsLocationStore(mContext, "routeos-locations.db"))
    {
      assertNotNull(store.newest(RouteOsApi.baseUrl(mContext), 987));
    }
    awaitState("live");
    assertEquals(2, mRequests.size());
    assertEquals(mRequests.get(0).getString("sample_id"), mRequests.get(1).getString("sample_id"));
    assertEquals(0, mContext.getSharedPreferences("routeos", 0).getInt("tracking_pending", -1));
  }

  @Test
  public void rateLimitRetainsAndRetriesTheSample() throws Exception
  {
    start(429, 201);
    awaitState("offline");
    assertEquals(1, mContext.getSharedPreferences("routeos", 0).getInt("tracking_pending", -1));
    awaitState("live");
    assertEquals(2, mRequests.size());
    assertEquals(mRequests.get(0).getString("sample_id"), mRequests.get(1).getString("sample_id"));
  }

  @Test
  public void endedRideDiscardsSamplesAndClearsLocalRide() throws Exception
  {
    start(409);
    var prefs = mContext.getSharedPreferences("routeos", 0);
    long deadline = System.nanoTime() + java.util.concurrent.TimeUnit.SECONDS.toNanos(20);
    while (prefs.getLong("active_ride_id", 0) != 0 && System.nanoTime() < deadline)
      Thread.sleep(50);
    assertEquals(0, prefs.getLong("active_ride_id", 0));
    try (var store = new RouteOsLocationStore(mContext, "routeos-locations.db"))
    {
      assertEquals(0, store.count(RouteOsApi.baseUrl(mContext), 987));
    }
  }

  @Test
  public void expiredAuthenticationKeepsTheSampleForReauthentication() throws Exception
  {
    start(401, 201);
    awaitState("auth_required");
    assertEquals(1, mContext.getSharedPreferences("routeos", 0).getInt("tracking_pending", -1));
    assertEquals(765, mContext.getSharedPreferences("routeos", 0).getLong("active_ride_id", 0));
    mUploader.start();
    awaitState("live");
    assertEquals(2, mRequests.size());
    assertEquals(mRequests.get(0).getString("sample_id"), mRequests.get(1).getString("sample_id"));
  }
}
