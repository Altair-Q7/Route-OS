import 'dart:ui' show Locale, PlatformDispatcher;

import 'generated/app_localizations.dart';

/// Picks the product language for the device.
///
/// An unsupported language falls back to English rather than to whichever locale
/// happens to be listed first, so a French phone never lands on Arabic.
Locale resolveLocale([String? deviceLanguage]) {
  final language =
      deviceLanguage ?? PlatformDispatcher.instance.locale.languageCode;
  return AppStrings.supportedLocales.firstWhere(
    (locale) => locale.languageCode == language,
    orElse: () => const Locale('en'),
  );
}
