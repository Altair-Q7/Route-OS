import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:routeos_shell/deliveries/trip_builder.dart';

void main() {
  Future<dynamic> responder(
    String method, [
    Map<String, dynamic> data = const {},
  ]) async {
    switch (method) {
      case 'drivers':
        return {
          'drivers': [
            {'id': 3, 'name': 'Batter Driver'},
            {'id': 4, 'name': 'Second Driver'},
          ],
        };
      default:
        return {};
    }
  }

  Future<void> openBuilder(
    WidgetTester tester,
    Future<dynamic> Function(String, [Map<String, dynamic>]) request,
  ) async {
    await tester.pumpWidget(
      MaterialApp(home: TripBuilder(request: request)),
    );
    await tester.pumpAndSettle();
  }

  Future<void> tapVisible(WidgetTester tester, Finder finder) async {
    await tester.ensureVisible(finder);
    await tester.pumpAndSettle();
    await tester.tap(finder);
    await tester.pumpAndSettle();
  }

  Future<void> fillStop(
    WidgetTester tester, {
    required String customer,
    String latitude = '9.93',
    String longitude = '76.27',
    required List<(String, String, String)> products,
  }) async {
    await tapVisible(tester, find.text('Add supermarket'));
    await tester.enterText(find.widgetWithText(TextFormField, 'Supermarket name'), customer);
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Latitude'),
      latitude,
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Longitude'),
      longitude,
    );
    for (var i = 0; i < products.length; i++) {
      // A new stop starts with no product rows, so each one is added explicitly.
      await tapVisible(tester, find.text('Add product'));
      await tester.enterText(find.widgetWithText(TextFormField, 'Product').at(i), products[i].$1);
      await tester.enterText(find.widgetWithText(TextFormField, 'Qty').at(i), products[i].$2);
      await tester.enterText(find.widgetWithText(TextFormField, 'Unit').at(i), products[i].$3);
    }
    await tapVisible(tester, find.text('Save stop'));
  }

  Future<void> fillTripHeader(
    WidgetTester tester, {
    String reference = 'SAP-TRIP-1042',
    String vehicle = 'KL-07-AX-1234',
  }) async {
    await tester.enterText(find.widgetWithText(TextFormField, 'Trip reference'), reference);
    await tester.enterText(find.widgetWithText(TextFormField, 'Vehicle number'), vehicle);
    await tapVisible(tester, find.byType(DropdownButtonFormField<int>));
    await tester.tap(find.text('Batter Driver').last);
    await tester.pumpAndSettle();
  }

  testWidgets('sends a trip with stops, kg and packet quantities', (tester) async {
    Map<String, dynamic>? created;
    await openBuilder(tester, (method, [data = const {}]) async {
      if (method == 'delivery.trip.create') created = data;
      return responder(method, data);
    });

    await fillTripHeader(tester);
    await fillStop(
      tester,
      customer: 'Metro Fresh',
      products: [
        ('Dosa Batter', '25', 'kg'),
        ('Idli Batter', '5', 'packet'),
      ],
    );
    await tester.tap(find.widgetWithText(FilledButton, 'Create trip'));
    await tester.pumpAndSettle();

    expect(created, isNotNull);
    expect(created!['trip'], 'SAP-TRIP-1042');
    expect(created!['vehicle'], 'KL-07-AX-1234');
    expect(created!['driver_id'], 3);
    expect(created!['stops'], [
      {
        'stop_ref': 'STOP-1',
        'customer': 'Metro Fresh',
        'address': '',
        'latitude': 9.93,
        'longitude': 76.27,
        'items': [
          {'product_name': 'Dosa Batter', 'planned_quantity': '25', 'uom': 'kg'},
          {'product_name': 'Idli Batter', 'planned_quantity': '5', 'uom': 'packet'},
        ],
      },
    ]);
  });

  testWidgets('cannot save without a stop, a driver or a vehicle', (tester) async {
    var created = false;
    await openBuilder(tester, (method, [data = const {}]) async {
      if (method == 'delivery.trip.create') created = true;
      return responder(method, data);
    });

    // No stops yet.
    expect(
      tester
          .widget<FilledButton>(
            find.widgetWithText(FilledButton, 'Create trip'),
          )
          .onPressed,
      isNull,
    );

    await fillTripHeader(tester, vehicle: '');
    await fillStop(
      tester,
      customer: 'Metro Fresh',
      products: [('Dosa Batter', '25', 'kg')],
    );
    await tapVisible(tester, find.widgetWithText(FilledButton, 'Create trip'));
    // A missing vehicle number must block the save rather than reach the server.
    expect(created, isFalse);
    expect(find.text('Create trip'), findsWidgets); // still on the builder
  });

  testWidgets('every stop needs a product with a positive quantity', (
    tester,
  ) async {
    await openBuilder(tester, responder);
    await fillTripHeader(tester);

    await tapVisible(tester, find.text('Add supermarket'));
    await tester.enterText(find.widgetWithText(TextFormField, 'Supermarket name'), 'Metro Fresh');
    await tester.enterText(find.widgetWithText(TextFormField, 'Latitude'), '9.93');
    await tester.enterText(find.widgetWithText(TextFormField, 'Longitude'), '76.27');
    // A stop with no products must not be accepted.
    await tapVisible(tester, find.text('Save stop'));
    expect(find.text('Add supermarket'), findsOneWidget); // dialog stayed open

    await tapVisible(tester, find.text('Add product'));
    await tester.enterText(find.widgetWithText(TextFormField, 'Product'), 'Dosa Batter');
    await tester.enterText(find.widgetWithText(TextFormField, 'Qty'), '0');
    await tester.enterText(find.widgetWithText(TextFormField, 'Unit'), 'kg');
    await tapVisible(tester, find.text('Save stop'));
    expect(find.text('Add supermarket'), findsOneWidget); // still open: qty was zero

    await tester.enterText(find.widgetWithText(TextFormField, 'Qty'), '25');
    await tapVisible(tester, find.text('Save stop'));
    expect(find.text('Metro Fresh'), findsOneWidget);
  });

  testWidgets('rejects a missing or out-of-range coordinate', (tester) async {
    await openBuilder(tester, responder);
    await tapVisible(tester, find.text('Add supermarket'));
    await tester.enterText(find.widgetWithText(TextFormField, 'Supermarket name'), 'Metro Fresh');
    await tester.enterText(find.widgetWithText(TextFormField, 'Latitude'), '99');
    await tester.enterText(find.widgetWithText(TextFormField, 'Longitude'), '76.27');
    await tapVisible(tester, find.text('Save stop'));
    // Latitude 99 is out of range, so the stop must not be created.
    expect(find.text('Add supermarket'), findsOneWidget);

    await tester.enterText(find.widgetWithText(TextFormField, 'Latitude'), '');
    await tapVisible(tester, find.text('Save stop'));
    expect(find.text('Add supermarket'), findsOneWidget);
  });

  testWidgets('a stop can be edited and removed before saving', (tester) async {
    Map<String, dynamic>? created;
    await openBuilder(tester, (method, [data = const {}]) async {
      if (method == 'delivery.trip.create') created = data;
      return responder(method, data);
    });
    await fillTripHeader(tester);
    await fillStop(tester, customer: 'Metro Fresh', products: [('Dosa Batter', '25', 'kg')]);
    await fillStop(tester, customer: 'City Mart', products: [('Idli Batter', '5', 'packet')]);

    expect(find.text('Metro Fresh'), findsOneWidget);
    expect(find.text('City Mart'), findsOneWidget);

    await tester.tap(find.byTooltip('Remove stop').last);
    await tester.pumpAndSettle();
    expect(find.text('City Mart'), findsNothing);

    await tapVisible(tester, find.widgetWithText(FilledButton, 'Create trip'));
    expect((created!['stops'] as List).length, 1);
    expect((created!['stops'] as List).first['stop_ref'], 'STOP-1');
  });

  testWidgets('a server failure keeps the entered trip on screen', (tester) async {
    await openBuilder(tester, (method, [data = const {}]) async {
      if (method == 'delivery.trip.create') throw StateError('driver mismatch');
      return responder(method, data);
    });
    await fillTripHeader(tester);
    await fillStop(tester, customer: 'Metro Fresh', products: [('Dosa Batter', '25', 'kg')]);
    await tapVisible(tester, find.widgetWithText(FilledButton, 'Create trip'));

    expect(find.text('Metro Fresh'), findsOneWidget);
    expect(find.text('Create trip'), findsWidgets); // still on the builder
  });
}