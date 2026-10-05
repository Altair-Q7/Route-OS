import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:routeos_shell/core/bridge.dart';
import 'package:routeos_shell/home/home.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final messenger =
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;

  setUp(() {
    messenger.setMockMethodCallHandler(
      const MethodChannel('routeos/v1/events'),
      (_) async => null,
    );
    messenger.setMockMethodCallHandler(
      SystemChannels.platform_views,
      (_) async => null,
    );
  });

  tearDown(() {
    messenger.setMockMethodCallHandler(Bridge.methods, null);
    messenger.setMockMethodCallHandler(
      const MethodChannel('routeos/v1/events'),
      null,
    );
    messenger.setMockMethodCallHandler(SystemChannels.platform_views, null);
  });

  Future<void> showHome(WidgetTester tester) =>
      tester.pumpWidget(const MaterialApp(home: RouteOsFlutterHome()));

  void emit(WidgetTester tester, String type, dynamic data) {
    tester.binding.channelBuffers.push(
      Bridge.events.name,
      const StandardMethodCodec().encodeSuccessEnvelope({
        'version': 1,
        'type': type,
        'data': data,
      }),
      (_) {},
    );
  }

  testWidgets('stale calculation results cannot overwrite the current route', (
    tester,
  ) async {
    final generations = <int>[];
    messenger.setMockMethodCallHandler(Bridge.methods, (call) async {
      if (call.method == 'calculate') {
        generations.add((call.arguments as Map)['data']['generation'] as int);
      }
      return switch (call.method) {
        'session' => {'id': 1, 'role': 'driver', 'name': 'Alice'},
        'draft.load' => {
          'ui_page': 'planner',
          'points': [
            {'id': 'a', 'latitude': 10, 'longitude': 77},
            {'id': 'b', 'latitude': 11, 'longitude': 77},
          ],
        },
        'routes' => [],
        _ => null,
      };
    });
    await showHome(tester);
    await tester.pump();
    final first = generations.single;
    emit(tester, 'map.tap', {'latitude': 12, 'longitude': 77});
    await tester.pump();
    final second = generations.last;
    expect(second, greaterThan(first));
    emit(tester, 'route.ready', {
      'generation': first,
      'distance_meters': 9000,
      'duration_seconds': 600,
    });
    await tester.pump();
    expect(find.textContaining('CALCULATING'), findsOneWidget);
    emit(tester, 'route.ready', {
      'generation': second,
      'distance_meters': 1000,
      'duration_seconds': 120,
    });
    await tester.pump();
    expect(find.text('1.0 km · 2 min'), findsOneWidget);
    emit(tester, 'route.failed', {
      'generation': first,
      'message': 'Old failure',
    });
    await tester.pump();
    expect(find.textContaining('READY'), findsOneWidget);
    expect(find.text('Old failure'), findsNothing);
    await tester.pumpWidget(const SizedBox.shrink());
  });

  testWidgets('server ride is restored without a local active ride ID', (
    tester,
  ) async {
    messenger.setMockMethodCallHandler(Bridge.methods, (call) async {
      return switch (call.method) {
        'session' => {'id': 1, 'role': 'driver', 'name': 'Alice'},
        'draft.load' => {},
        'routes' => [],
        'ride.restore' => {'id': 12},
        _ => null,
      };
    });
    await showHome(tester);
    await tester.pumpAndSettle();

    expect(find.text('End ride'), findsOneWidget);
    expect(find.text('Record route'), findsNothing);
    await tester.pumpWidget(const SizedBox.shrink());
  });

  testWidgets('missing server ride clears stale navigation UI', (tester) async {
    final commands = <String>[];
    messenger.setMockMethodCallHandler(Bridge.methods, (call) async {
      commands.add(call.method);
      return switch (call.method) {
        'session' => {
          'id': 1,
          'role': 'driver',
          'name': 'Alice',
          'active_ride_id': 12,
        },
        'draft.load' => {},
        'routes' => [],
        _ => null,
      };
    });
    await showHome(tester);
    await tester.pumpAndSettle();

    expect(commands, contains('ride.restore'));
    expect(find.text('End ride'), findsNothing);
    expect(find.text('Record route'), findsOneWidget);
    await tester.pumpWidget(const SizedBox.shrink());
  });

  testWidgets('disposing while a draft loads does not update disposed state', (
    tester,
  ) async {
    final draft = Completer<dynamic>();
    messenger.setMockMethodCallHandler(Bridge.methods, (call) async {
      return switch (call.method) {
        'session' => {'id': 1, 'role': 'driver', 'name': 'Alice'},
        'draft.load' => await draft.future,
        _ => null,
      };
    });
    await showHome(tester);
    await tester.pump();
    await tester.pumpWidget(const SizedBox.shrink());
    draft.complete({'points': []});
    await tester.pump();

    expect(tester.takeException(), isNull);
  });

  testWidgets('expired session retains active navigation and offers sign in', (
    tester,
  ) async {
    messenger.setMockMethodCallHandler(Bridge.methods, (call) async {
      return switch (call.method) {
        'session' => {
          'id': 1,
          'role': 'driver',
          'name': 'Alice',
          'active_ride_id': 12,
        },
        'draft.load' => {},
        'routes' => throw PlatformException(
          code: 'AUTH_EXPIRED',
          message: 'Sign in again',
        ),
        'ride.restore' => throw PlatformException(
          code: 'AUTH_EXPIRED',
          message: 'Sign in again',
        ),
        _ => null,
      };
    });
    await showHome(tester);
    await tester.pumpAndSettle();
    expect(find.text('End ride'), findsOneWidget);
    expect(find.text('Sign in'), findsOneWidget);
    await tester.tap(find.text('Sign in'));
    await tester.pumpAndSettle();
    expect(find.widgetWithText(TextField, 'Account name'), findsOneWidget);
    expect(find.text('Alice'), findsOneWidget);
    await tester.pumpWidget(const SizedBox.shrink());
  });
}
