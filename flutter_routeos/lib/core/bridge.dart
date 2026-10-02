import 'package:flutter/services.dart';

class Bridge {
  static const methods = MethodChannel('routeos/v1/methods');
  static const events = EventChannel('routeos/v1/events');
  static Future<dynamic> call(
    String method, [
    Map<String, dynamic> data = const {},
  ]) => methods.invokeMethod(method, {'version': 1, 'data': data});
}
