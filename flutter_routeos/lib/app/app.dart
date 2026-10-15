import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import '../home/home.dart';
import '../l10n/generated/app_localizations.dart';
import '../l10n/locale.dart';

class RouteOsShell extends StatelessWidget {
  const RouteOsShell({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner: false,
    onGenerateTitle: (context) => AppStrings.of(context).appTitle,
    localizationsDelegates: const [
      AppStrings.delegate,
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
    ],
    // Arabic reads right to left; the rest of the supported set is left to right.
    supportedLocales: AppStrings.supportedLocales,
    locale: resolveLocale(),
    theme: ThemeData(
      brightness: Brightness.dark,
      useMaterial3: true,
      scaffoldBackgroundColor: const Color(0xff081219),
      colorScheme: const ColorScheme.dark(
        primary: Color(0xff10df9b),
        onPrimary: Color(0xff032118),
        primaryContainer: Color(0xff075f43),
        onPrimaryContainer: Color(0xffd0ffec),
        secondary: Color(0xff7ed7ff),
        surface: Color(0xff101d26),
        surfaceContainerHighest: Color(0xff22333e),
        error: Color(0xffffb4ab),
      ),
      visualDensity: VisualDensity.standard,
      cardTheme: CardThemeData(
        color: const Color(0xff15232e),
        elevation: 1,
        margin: const EdgeInsets.symmetric(vertical: 5),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(18),
          side: const BorderSide(color: Color(0xff263945)),
        ),
      ),
      navigationBarTheme: const NavigationBarThemeData(
        height: 72,
        backgroundColor: Color(0xff101d26),
        indicatorColor: Color(0xff075f43),
        labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size(48, 48),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          minimumSize: const Size(48, 48),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: const Color(0xff172630),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 14,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide.none,
        ),
      ),
    ),
    home: const RouteOsFlutterHome(),
  );
}
