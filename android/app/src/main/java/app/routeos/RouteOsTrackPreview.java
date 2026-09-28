package app.routeos;

import android.content.Context;
import android.content.SharedPreferences;
import androidx.annotation.NonNull;
import app.organicmaps.sdk.bookmarks.data.BookmarkCategory;
import app.organicmaps.sdk.bookmarks.data.BookmarkManager;
import java.io.File;

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
  private static final String FILE_PREFIX = "routeos-route-";

  private RouteOsTrackPreview() {}

  /**
   * Shows {@code file} as the single RouteOS preview, removing the previous preview and any
   * stale {@code routeos-route-*} categories left behind by older previews.
   */
  public static void replace(@NonNull Context context, @NonNull File file, long routeId) {
    clear(context);
    BookmarkManager.INSTANCE.loadBookmarksFile(file.getAbsolutePath(), true);
    long kept = -1;
    String wanted = FILE_PREFIX + routeId;
    for (BookmarkCategory category : BookmarkManager.INSTANCE.getCategories()) {
      String name = category.getName();
      if (name == null || !name.startsWith(FILE_PREFIX)) continue;
      if (name.equals(wanted) || name.startsWith(wanted + ".")) {
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
      prefs(context).edit().remove(KEY_CATEGORY_ID).apply();
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
