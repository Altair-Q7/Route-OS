package app.routeos;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import android.content.SharedPreferences;
import java.util.HashMap;
import java.util.Map;
import org.junit.Before;
import org.junit.Test;

public class RouteOsDraftStoreTest
{
  private final Map<String, String> mValues = new HashMap<>();
  private final SharedPreferences mPrefs = mock(SharedPreferences.class);
  private long mDriverId;

  @Before
  public void setUp()
  {
    SharedPreferences.Editor editor = mock(SharedPreferences.Editor.class);
    when(mPrefs.edit()).thenReturn(editor);
    when(mPrefs.getLong("driver_id", 0)).thenAnswer(call -> mDriverId);
    when(mPrefs.contains(anyString())).thenAnswer(call -> mValues.containsKey(call.getArgument(0)));
    when(mPrefs.getString(anyString(), anyString()))
        .thenAnswer(call -> mValues.getOrDefault(call.getArgument(0), call.getArgument(1)));
    when(editor.putString(anyString(), anyString())).thenAnswer(call -> {
      mValues.put(call.getArgument(0), call.getArgument(1));
      return editor;
    });
    when(editor.remove(anyString())).thenAnswer(call -> {
      mValues.remove(call.getArgument(0));
      return editor;
    });
  }

  @Test
  public void switchingAccountsDoesNotExposeAnotherDriversDraft()
  {
    mDriverId = 1;
    RouteOsDraftStore.save(mPrefs, "Alice's draft");
    mDriverId = 2;
    assertEquals("{}", RouteOsDraftStore.load(mPrefs));
    RouteOsDraftStore.save(mPrefs, "Bob's draft");
    mDriverId = 1;
    assertEquals("Alice's draft", RouteOsDraftStore.load(mPrefs));
    mDriverId = 2;
    assertEquals("Bob's draft", RouteOsDraftStore.load(mPrefs));
  }

  @Test
  public void legacyDraftIsAssignedOnceWithoutReplacingAnExistingDraft()
  {
    mValues.put("planner_draft", "Legacy draft");
    assertEquals("{}", RouteOsDraftStore.load(mPrefs));
    mDriverId = 1;
    assertEquals("Legacy draft", RouteOsDraftStore.load(mPrefs));
    assertFalse(mValues.containsKey("planner_draft"));
    mDriverId = 2;
    assertEquals("{}", RouteOsDraftStore.load(mPrefs));
    RouteOsDraftStore.save(mPrefs, "New draft");
    mValues.put("planner_draft", "Old draft");
    assertEquals("New draft", RouteOsDraftStore.load(mPrefs));
  }

  @Test
  public void sameDriverIdOnAnotherServerHasADifferentDraft()
  {
    mDriverId = 1;
    RouteOsDraftStore.save(mPrefs, "First server");
    mValues.put("api_base_url", "https://other.example");
    assertEquals("{}", RouteOsDraftStore.load(mPrefs));
    RouteOsDraftStore.save(mPrefs, "Other server");
    mValues.remove("api_base_url");
    assertEquals("First server", RouteOsDraftStore.load(mPrefs));
  }

  @Test
  public void signedOutEditsCannotOverwriteAnAccountsDraft()
  {
    mDriverId = 1;
    RouteOsDraftStore.save(mPrefs, "Saved draft");
    mDriverId = 0;
    RouteOsDraftStore.save(mPrefs, "Signed-out draft");
    mDriverId = 1;
    assertEquals("Saved draft", RouteOsDraftStore.load(mPrefs));
  }
}
