import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:routeos_shell/deliveries/delivery_reports.dart';

import 'helpers.dart';

void main() {
  Map<String, dynamic> trip({
    String reference = 'SAP-TRIP-1',
    String driver = 'Batter Driver',
    String status = 'Delivered',
    List<Map<String, dynamic>>? stops,
  }) => {
        'id': 1,
        'trip': reference,
        'status': status,
        'driver_name': driver,
        'vehicle': 'KL-07-AX-1234',
        'updated_at': '2026-10-12T09:00:00+00:00',
        'surplus': <Map<String, dynamic>>[],
        'stops': stops ??
            [
              {
                'id': 'S1',
                'customer': 'Metro Fresh',
                'status': 'delivered',
                'reason': '',
                'items': [
                  {
                    'product_name': 'Idli Batter',
                    'uom': 'packet',
                    'planned_quantity': '5',
                    'delivered_quantity': '5',
                  }
                ],
              }
            ],
      };

  Future<dynamic> Function(String, [Map<String, dynamic>]) responder(
        Map<String, dynamic> payload) =>
    (String method, [Map<String, dynamic> data = const {}]) async =>
        method == 'reports.deliveries' ? payload : <String, dynamic>{};

  testWidgets('shows product totals and trips', (tester) async {
    await tester.pumpWidget(wrapForTest(DeliveryReports(
      request: responder({
        'trips': [trip()],
        'product_totals': [
          {'product_name': 'Idli Batter', 'uom': 'packet', 'planned_quantity': '10', 'delivered_quantity': '10'}
        ],
        'shortages': <Map<String, dynamic>>[],
      }),
    )));
    await tester.pumpAndSettle();

    expect(find.text('Totals by product'), findsOneWidget);
    expect(find.text('Idli Batter (packet)'), findsOneWidget);
    expect(find.text('10 / 10'), findsOneWidget);
    expect(find.text('SAP-TRIP-1'), findsOneWidget);
    expect(find.text('Batter Driver · Delivered'), findsOneWidget);
    // Nothing is short, so the shortage section is absent.
    expect(find.text('Shortages and failures'), findsNothing);
  });

  testWidgets('a shortage is called out with the reason', (tester) async {
    await tester.pumpWidget(wrapForTest(DeliveryReports(
      request: responder({
        'trips': [
          trip(
            status: 'Closed with shortages',
            stops: [
              {
                'id': 'S1',
                'customer': 'Metro Fresh',
                'status': 'partial',
                'reason': 'Shop had no storage',
                'items': [
                  {
                    'product_name': 'Dosa Batter',
                    'uom': 'kg',
                    'planned_quantity': '25',
                    'delivered_quantity': '22',
                  }
                ],
              }
            ],
          )
        ],
        'product_totals': [
          {'product_name': 'Dosa Batter', 'uom': 'kg', 'planned_quantity': '25', 'delivered_quantity': '22'}
        ],
        'shortages': [
          {
            'trip': 'SAP-TRIP-1',
            'customer': 'Metro Fresh',
            'reason': 'Shop had no storage',
            'items': [
              {
                'product_name': 'Dosa Batter',
                'uom': 'kg',
                'planned_quantity': '25',
                'delivered_quantity': '22',
              }
            ],
          }
        ],
      }),
    )));
    await tester.pumpAndSettle();

    expect(find.text('Shortages and failures'), findsOneWidget);
    expect(find.text('Metro Fresh · SAP-TRIP-1'), findsOneWidget);
    expect(find.textContaining('22/25 kg Dosa Batter'), findsOneWidget);
    expect(find.textContaining('Shop had no storage'), findsOneWidget);
    expect(find.text('22 / 25'), findsOneWidget);
  });

  testWidgets('an empty history says so rather than showing a blank screen', (
    tester,
  ) async {
    await tester.pumpWidget(wrapForTest(DeliveryReports(
      request: responder({
        'trips': <Map<String, dynamic>>[],
        'product_totals': <Map<String, dynamic>>[],
        'shortages': <Map<String, dynamic>>[],
      }),
    )));
    await tester.pumpAndSettle();
    expect(find.text('No deliveries recorded yet.'), findsOneWidget);
  });

  testWidgets('a failure can be retried', (tester) async {
    var failing = true;
    await tester.pumpWidget(wrapForTest(DeliveryReports(
      request: (String method, [Map<String, dynamic> data = const {}]) async {
        if (method != 'reports.deliveries') return {};
        if (failing) throw StateError('server unreachable');
        return {
          'trips': [trip()],
          'product_totals': <Map<String, dynamic>>[],
          'shortages': <Map<String, dynamic>>[],
        };
      },
    )));
    await tester.pumpAndSettle();
    expect(find.textContaining('server unreachable'), findsOneWidget);

    failing = false;
    await tester.tap(find.byTooltip('Refresh'));
    await tester.pumpAndSettle();
    expect(find.text('SAP-TRIP-1'), findsOneWidget);
    expect(find.textContaining('server unreachable'), findsNothing);
  });

  testWidgets('the report renders in Arabic', (tester) async {
    await tester.pumpWidget(wrapForTest(
      DeliveryReports(request: responder({
        'trips': [trip()],
        'product_totals': <Map<String, dynamic>>[],
        'shortages': <Map<String, dynamic>>[],
      })),
      deviceLanguage: 'ar',
    ));
    await tester.pumpAndSettle();
    expect(find.text('تقارير التسليم'), findsOneWidget);
    expect(find.text('الإجماليات حسب المنتج'), findsNothing);
    expect(find.text('الرحلات'), findsOneWidget);
  });
}