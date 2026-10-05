package app.routeos;

import android.content.ContentValues;
import android.content.Context;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;
import org.json.JSONException;
import org.json.JSONObject;

/** Bounded telemetry outbox. Server and account are part of every queued sample's identity. */
public final class RouteOsLocationStore extends SQLiteOpenHelper
{
  public static final int MAX_SAMPLES = 1000;

  public record Sample(long id, long rideId, JSONObject body)
  {
  }

  public RouteOsLocationStore(Context context, String databaseName)
  {
    super(context, databaseName, null, 1);
    setWriteAheadLoggingEnabled(true);
  }

  @Override
  public void onCreate(SQLiteDatabase db)
  {
    db.execSQL("CREATE TABLE samples (id INTEGER PRIMARY KEY AUTOINCREMENT, server TEXT NOT NULL, "
               + "driver_id INTEGER NOT NULL, ride_id INTEGER NOT NULL, body TEXT NOT NULL)");
    db.execSQL("CREATE INDEX idx_samples_scope ON samples(server, driver_id, id DESC)");
  }

  @Override
  public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion)
  {}

  public void enqueue(String server, long driverId, long rideId, JSONObject body)
  {
    SQLiteDatabase db = getWritableDatabase();
    db.beginTransaction();
    try
    {
      ContentValues values = new ContentValues();
      values.put("server", server);
      values.put("driver_id", driverId);
      values.put("ride_id", rideId);
      values.put("body", body.toString());
      db.insertOrThrow("samples", null, values);
      // Prefer recent telemetry if an outage exceeds the bounded history window.
      db.execSQL("DELETE FROM samples WHERE id NOT IN (SELECT id FROM samples ORDER BY id DESC LIMIT ?)",
                 new Object[] {MAX_SAMPLES});
      db.setTransactionSuccessful();
    }
    finally
    {
      db.endTransaction();
    }
  }

  public Sample newest(String server, long driverId) throws JSONException
  {
    try (var cursor = getReadableDatabase().rawQuery(
             "SELECT id, ride_id, body FROM samples WHERE server=? AND driver_id=? ORDER BY id DESC LIMIT 1",
             new String[] {server, Long.toString(driverId)}))
    {
      if (!cursor.moveToFirst())
        return null;
      return new Sample(cursor.getLong(0), cursor.getLong(1), new JSONObject(cursor.getString(2)));
    }
  }

  public int count(String server, long driverId)
  {
    try (var cursor = getReadableDatabase().rawQuery("SELECT COUNT(*) FROM samples WHERE server=? AND driver_id=?",
                                                     new String[] {server, Long.toString(driverId)}))
    {
      cursor.moveToFirst();
      return cursor.getInt(0);
    }
  }

  public void acknowledge(long sampleId)
  {
    getWritableDatabase().delete("samples", "id=?", new String[] {Long.toString(sampleId)});
  }

  public void discardRide(String server, long driverId, long rideId)
  {
    getWritableDatabase().delete("samples", "server=? AND driver_id=? AND ride_id=?",
                                 new String[] {server, Long.toString(driverId), Long.toString(rideId)});
  }
}
