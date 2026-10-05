package app.routeos;

import android.content.SharedPreferences;

/** Account-owned drafts, including a one-time migration of the original shared draft. */
public final class RouteOsDraftStore
{
  private RouteOsDraftStore() {}

  private static String key(SharedPreferences prefs)
  {
    long driverId = prefs.getLong("driver_id", 0);
    return driverId > 0 ? "planner_draft_" + prefs.getString("api_base_url", RouteOsApi.DEFAULT_API) + "_" + driverId
                        : null;
  }

  public static void save(SharedPreferences prefs, String draft)
  {
    String key = key(prefs);
    if (key != null)
      prefs.edit().putString(key, draft).apply();
  }

  public static String load(SharedPreferences prefs)
  {
    String key = key(prefs);
    if (key == null)
      return "{}";
    String legacyKey = "planner_draft_" + prefs.getLong("driver_id", 0);
    if (!prefs.contains(legacyKey))
      legacyKey = "planner_draft";
    if (prefs.contains(legacyKey))
    {
      var editor = prefs.edit();
      if (!prefs.contains(key))
        editor.putString(key, prefs.getString(legacyKey, "{}"));
      editor.remove(legacyKey).apply();
    }
    return prefs.getString(key, "{}");
  }
}
