import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:routeos_shell/l10n/generated/app_localizations.dart';
import 'package:routeos_shell/l10n/locale.dart';

/// Wraps a widget under test with the product's localisation delegates.
///
/// Uses the same resolution as the app, so a test of an unsupported language
/// exercises the real fallback rather than Flutter's first-locale default.
Widget wrapForTest(Widget child, {String? deviceLanguage}) => MaterialApp(
  localizationsDelegates: const [
    AppStrings.delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
  ],
  supportedLocales: AppStrings.supportedLocales,
  locale: resolveLocale(deviceLanguage),
  home: child,
);
