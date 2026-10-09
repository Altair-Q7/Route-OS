import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:routeos_shell/deliveries/delivery_panel.dart';

void main() {
  final assignment = <String, dynamic>{
    'id': 1,
    'trip': 'Trip A',
    'driver_name': 'Driver A',
    'vehicle': 'KL-01',
    'status': 'Assigned',
    'sync_pending': true,
    'ride_id': null,
    'stops': [
      <String, dynamic>{
        'id': 'stop-a',
        'customer': 'Customer A',
        'address_text': 'Street A',
        'status': 'pending',
        'reason': '',
      },
    ],
  };

  testWidgets('driver sees assignments and links freshly restored ride ID', (
    tester,
  ) async {
    final calls = <String>[];
    Future<dynamic> request(
      String method, [
      Map<String, dynamic> data = const {},
    ]) async {
      calls.add(method);
      if (method == 'deliveries') {
        return {
          'assignments': [assignment],
        };
      }
      if (method == 'session') return {'active_ride_id': 77};
      if (method == 'delivery.ride') expect(data['ride_id'], 77);
      return {};
    }

    await tester.pumpWidget(
      MaterialApp(
        home: DeliveryPanel(request: request, isAdmin: false, activeRideId: 0),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Trip A · Assigned'), findsOneWidget);
    expect(find.text('Assign ERPNext trip'), findsNothing);
    expect(find.text('delivered'), findsNothing);
    await tester.tap(find.text('Link my current ride'));
    await tester.pumpAndSettle();
    expect(calls, contains('delivery.ride'));
  });

  testWidgets('ERP error is visible and refresh can recover', (tester) async {
    var fail = true;
    Future<dynamic> request(
      String method, [
      Map<String, dynamic> data = const {},
    ]) async {
      if (fail) throw StateError('ERP unavailable');
      if (method == 'session') return {};
      return {'assignments': []};
    }

    await tester.pumpWidget(
      MaterialApp(
        home: DeliveryPanel(request: request, isAdmin: true, activeRideId: 0),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.textContaining('ERP unavailable'), findsOneWidget);
    fail = false;
    await tester.tap(find.byTooltip('Refresh deliveries'));
    await tester.pumpAndSettle();
    expect(find.textContaining('ERP unavailable'), findsNothing);
    expect(find.text('No delivery assignments'), findsOneWidget);
  });

  testWidgets('opening delivery screen never confirms a pending stop', (
    tester,
  ) async {
    final calls = <String>[];
    Future<dynamic> request(
      String method, [
      Map<String, dynamic> data = const {},
    ]) async {
      calls.add(method);
      if (method == 'session') return {};
      return {
        'assignments': [
          {...assignment, 'ride_id': 3},
        ],
      };
    }

    await tester.pumpWidget(
      MaterialApp(
        home: DeliveryPanel(request: request, isAdmin: false, activeRideId: 3),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('delivered'), findsOneWidget);
    expect(calls, isNot(contains('delivery.confirm')));
    await tester.tap(find.text('delivered'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('Confirm delivered?'), findsOneWidget);
    expect(calls, isNot(contains('delivery.confirm')));
    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();
    expect(calls, isNot(contains('delivery.confirm')));
  });

  testWidgets('delivered product quantities are visible with their units', (
    tester,
  ) async {
    Future<dynamic> request(
      String method, [
      Map<String, dynamic> data = const {},
    ]) async {
      if (method == 'session') return {};
      return {
        'assignments': [
          {
            ...assignment,
            'ride_id': 3,
            'stops': [
              {
                'id': 'stop-a',
                'customer': 'Customer A',
                'address_text': 'Street A',
                'status': 'partial',
                'reason': 'Customer accepted fewer goods',
                'items': [
                  {
                    'id': 'milk',
                    'product_name': 'Milk',
                    'planned_quantity': '10',
                    'delivered_quantity': '7.5',
                    'uom': 'L',
                  },
                  {
                    'id': 'batter',
                    'product_name': 'Batter',
                    'planned_quantity': '2',
                    'delivered_quantity': '1.25',
                    'uom': 'kg',
                  },
                ],
              },
            ],
          },
        ],
      };
    }

    await tester.pumpWidget(
      MaterialApp(
        home: DeliveryPanel(request: request, isAdmin: true, activeRideId: 0),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Milk: 7.5 / 10 L delivered'), findsOneWidget);
    expect(find.text('Batter: 1.25 / 2 kg delivered'), findsOneWidget);
    expect(
      find.text('partial'),
      findsNothing,
    ); // confirmed outcomes have no editable action buttons
  });

  testWidgets(
    'confirmation sends explicit quantities rather than guessing delivered amounts',
    (tester) async {
      Map<String, dynamic>? confirmation;
      Future<dynamic> request(
        String method, [
        Map<String, dynamic> data = const {},
      ]) async {
        if (method == 'session') return {};
        if (method == 'delivery.confirm') {
          confirmation = data;
          return {};
        }
        return {
          'assignments': [
            {
              ...assignment,
              'ride_id': 3,
              'stops': [
                {
                  'id': 'stop-a',
                  'customer': 'Customer A',
                  'address_text': 'Street A',
                  'status': 'pending',
                  'reason': '',
                  'items': [
                    {
                      'id': 'milk',
                      'product_name': 'Milk',
                      'planned_quantity': '10',
                      'delivered_quantity': '0',
                      'uom': 'L',
                    },
                    {
                      'id': 'batter',
                      'product_name': 'Batter',
                      'planned_quantity': '2',
                      'delivered_quantity': '0',
                      'uom': 'kg',
                    },
                  ],
                },
              ],
            },
          ],
        };
      }

      await tester.pumpWidget(
        MaterialApp(
          home: DeliveryPanel(
            request: request,
            isAdmin: false,
            activeRideId: 3,
          ),
        ),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.text('delivered'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));
      await tester.tap(find.text('Confirm'));
      await tester.pump();
      expect(confirmation, isNull);
      expect(find.textContaining('For a shortage'), findsWidgets);
      final fields = find.byType(TextFormField);
      await tester.enterText(fields.at(0), '10');
      await tester.enterText(fields.at(1), '2');
      await tester.tap(find.text('Confirm'));
      await tester.pumpAndSettle();
      expect(confirmation!['items'], [
        {'id': 'milk', 'delivered_quantity': '10'},
        {'id': 'batter', 'delivered_quantity': '2'},
      ]);
    },
  );
}
