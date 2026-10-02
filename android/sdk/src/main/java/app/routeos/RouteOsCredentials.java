package app.routeos;

import android.content.Context;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/** Tokens are encrypted with a non-exportable Android Keystore key, never logged. */
public final class RouteOsCredentials {
  private static final String ALIAS = "routeos.session.v1";
  private RouteOsCredentials() {}
  private static SecretKey key() throws Exception {
    KeyStore keys = KeyStore.getInstance("AndroidKeyStore"); keys.load(null);
    if (!keys.containsAlias(ALIAS)) {
      KeyGenerator generator = KeyGenerator.getInstance("AES", "AndroidKeyStore");
      generator.init(new KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
          .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build());
      generator.generateKey();
    }
    return (SecretKey) keys.getKey(ALIAS, null);
  }
  public static synchronized void store(Context context, String token) throws Exception {
    Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding"); cipher.init(Cipher.ENCRYPT_MODE, key());
    String value = Base64.encodeToString(cipher.getIV(), Base64.NO_WRAP) + ":"
        + Base64.encodeToString(cipher.doFinal(token.getBytes(StandardCharsets.UTF_8)), Base64.NO_WRAP);
    context.getSharedPreferences("routeos_credentials", 0).edit().putString("session", value).apply();
    context.getSharedPreferences("routeos", 0).edit().remove("auth_token").apply();
  }
  public static synchronized String read(Context context) {
    try {
      String value = context.getSharedPreferences("routeos_credentials", 0).getString("session", null);
      if (value == null) {
        String legacy = context.getSharedPreferences("routeos", 0).getString("auth_token", null);
        if (legacy != null) { store(context, legacy); return legacy; }
        return null;
      }
      String[] parts = value.split(":");
      Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
      cipher.init(Cipher.DECRYPT_MODE, key(), new GCMParameterSpec(128, Base64.decode(parts[0], Base64.NO_WRAP)));
      return new String(cipher.doFinal(Base64.decode(parts[1], Base64.NO_WRAP)), StandardCharsets.UTF_8);
    } catch (Exception unavailable) { clear(context); return null; }
  }
  public static void clear(Context context) { context.getSharedPreferences("routeos_credentials", 0).edit().clear().apply(); }
}
