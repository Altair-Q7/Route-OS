import 'package:flutter/material.dart';
import '../home/home.dart';

class RouteOsShell extends StatelessWidget {
  const RouteOsShell({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner: false,
    title: 'RouteOS',
    theme: ThemeData(
      brightness: Brightness.dark,
      useMaterial3: true,
      scaffoldBackgroundColor: const Color(0xff081219),
      colorScheme:
          ColorScheme.fromSeed(
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
