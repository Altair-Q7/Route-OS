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
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xff10df9b),
            brightness: Brightness.dark,
          ).copyWith(
            primary: const Color(0xff10df9b),
            onPrimary: const Color(0xff081219),
          ),
          cardTheme: const CardThemeData(color: Color(0xff15232e)),
          inputDecorationTheme: InputDecorationTheme(
            filled: true,
            fillColor: const Color(0xff172630),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(18)),
          ),
        ),
        home: const RouteOsFlutterHome(),
      );
}
