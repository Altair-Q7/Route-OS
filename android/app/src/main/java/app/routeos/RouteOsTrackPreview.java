package app.routeos;

import android.content.Context;
import android.content.SharedPreferences;
import androidx.annotation.NonNull;
import app.organicmaps.sdk.bookmarks.data.BookmarkCategory;
import app.organicmaps.sdk.bookmarks.data.BookmarkManager;
import java.util.ArrayList;
import java.io.File;
import org.json.JSONArray;

/**
 * Single-preview hygiene for RouteOS map tracks (#24).
 *
 * <p>Every route preview/import used to call {@code loadBookmarksFile} and leave the track visible
 * for the whole session, so each preview stacked another polyline on the map — for a two-point
 * drawn route that leftover is literally one straight hub-to-destination segment drawn over the
 * live road route. This helper guarantees at most one RouteOS preview is ever on the map, and
 * removes it entirely once a ride starts (native guidance becomes the source of truth).
 *
 * <p>All methods must run on the UI thread; BookmarkManager is main-thread bound.
 */
public final class RouteOsTrackPreview {
  private static final String PREFS = "routeos";
  private static final String KEY_CATEGORY_ID = "preview_category_id";
  private static final String KEY_CATEGORY_NAME = "preview_category_name";
  private static final String FILE_PREFIX = "routeos-route-";

  private RouteOsTrackPreview() {}

  /**
   * Shows {@code file} as the single RouteOS preview, removing the previous preview and any
   * stale {@code routeos-route-*} categories left behind by older previews.
   */
  public static void replace(@NonNull Context context, @NonNull File file, long routeId) {
    clear(context);
    String fileName = file.getName();
    String categoryName = fileName.substring(0, fileName.lastIndexOf('.'));
    prefs(context).edit().putString(KEY_CATEGORY_NAME, categoryName).apply();
    BookmarkManager.INSTANCE.loadBookmarksFile(file.getAbsolutePath(), true);
    retainImported(context, routeId);
  }

  /** Called again after asynchronous import updates the native category cache. */
  public static void retainImported(@NonNull Context context, long routeId) {
    long kept = -1;
    String wanted = prefs(context).getString(KEY_CATEGORY_NAME, FILE_PREFIX + routeId);
    for (BookmarkCategory category : new ArrayList<>(BookmarkManager.INSTANCE.getCategories())) {
      String name = category.getName();
      if (name == null || !name.startsWith(FILE_PREFIX)) continue;
      if (name.equals(wanted)) {
        kept = category.getId();
        continue;
      }
      deleteQuietly(category.getId());
    }
    prefs(context).edit().putLong(KEY_CATEGORY_ID, kept).apply();
  }

  /** Removes the current RouteOS preview from the map, if any. */
  public static void clear(@NonNull Context context) {
    long id = prefs(context).getLong(KEY_CATEGORY_ID, -1);
    if (id != -1) {
      deleteQuietly(id);
    }
    // Also sweep previews created before the persisted category id was introduced. This is
    // important on upgraded installs: a stale category can otherwise keep its polyline visible
    // even after the current preview and native route plan have been cancelled.
    for (BookmarkCategory category : new ArrayList<>(BookmarkManager.INSTANCE.getCategories())) {
      String name = category.getName();
      if (name != null && name.startsWith(FILE_PREFIX))
        deleteQuietly(category.getId());
      for (long trackId : category.getTrackIds()) {
        try {
          String trackName = BookmarkManager.INSTANCE.getTrack(trackId).getName();
          if (trackName != null && trackName.startsWith(FILE_PREFIX))
            BookmarkManager.INSTANCE.deleteTrack(trackId);
        } catch (Exception ignored) {}
      }
    }
    prefs(context).edit().remove(KEY_CATEGORY_ID).remove(KEY_CATEGORY_NAME).apply();
  }

  /** Removes tracks imported by the legacy preview code, which used the route's display name. */
  public static void clearLegacyRecordedTracks(@NonNull Context context, @NonNull JSONArray routes) {
    ArrayList<String> names = new ArrayList<>();
    for (int i = 0; i < routes.length(); i++) {
      String type = routes.optJSONObject(i) == null ? "" : routes.optJSONObject(i).optString("route_type");
      if ("recorded".equals(type))
        names.add(routes.optJSONObject(i).optString("name"));
    }
    if (names.isEmpty()) return;
    for (BookmarkCategory category : new ArrayList<>(BookmarkManager.INSTANCE.getCategories())) {
      for (long trackId : category.getTrackIds()) {
        try {
          String trackName = BookmarkManager.INSTANCE.getTrack(trackId).getName();
          if (names.contains(trackName))
            BookmarkManager.INSTANCE.deleteTrack(trackId);
        } catch (Exception ignored) {}
      }
    }
  }

  private static void deleteQuietly(long categoryId) {
    try {
      BookmarkManager.INSTANCE.deleteCategory(categoryId);
    } catch (Exception ignored) {}
  }

  private static SharedPreferences prefs(Context context) {
    return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
  }
}
