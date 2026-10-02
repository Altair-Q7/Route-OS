import 'package:flutter/material.dart';
import 'app/app.dart';
import 'core/bridge.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  FlutterError.onError = (details) {
    FlutterError.presentError(details);
    Bridge.call('diagnostic', {'message': details.exceptionAsString()});
  };
  runApp(const RouteOsShell());
}
