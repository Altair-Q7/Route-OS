import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'helpers.dart';
import 'package:routeos_shell/deliveries/supermarket_directory.dart';

void main() {
  Map<String, dynamic> shop(
    String name, {
    String address = 'MG Road',
    int active = 1,
    List<Map<String, dynamic>>? order,
  }) => {
    'id': 1,
    'name': name,
    'address': address,
    'latitude': 9.93,
    'longitude': 76.27,
    'active': active,
    'standing_order':
        order ??
        [
          {'product_name': 'Idli Batter', 'uom': 'packet', 'quantity': '5'},
        ],
  };

  Future<void> open(
    WidgetTester tester,
    Future<dynamic> Function(String, [Map<String, dynamic>]) request,
  ) async {
    await tester.pumpWidget(
      wrapForTest(SupermarketDirectory(request: request)),
    );
    await tester.pumpAndSettle();
  }

  Future<dynamic> listing(List<Map<String, dynamic>> shops) =>
      Future.value({'supermarkets': shops});

  testWidgets('shows each supermarket with its usual allocation', (
    tester,
  ) async {
    await open(
      tester,
      (method, [data = const {}]) async => listing([
        shop('Metro Fresh'),
        shop(
          'City Mart',
          active: 0,
          order: [
            {'product_name': 'Dosa Batter', 'uom': 'kg', 'quantity': '10'},
          ],
        ),
      ]),
    );

    expect(find.text('Metro Fresh'), findsOneWidget);
    expect(find.text('5 packet Idli Batter'), findsOneWidget);
    expect(find.text('City Mart'), findsOneWidget);
    expect(find.text('10 kg Dosa Batter'), findsOneWidget);
    expect(find.text('Inactive'), findsOneWidget);
  });

  testWidgets('a shop without an allocation says so', (tester) async {
    await open(
      tester,
      (method, [data = const {}]) async =>
          listing([shop('Metro Fresh', order: const [])]),
    );
    expect(find.text('No usual allocation yet'), findsOneWidget);
  });

  testWidgets('adding a supermarket sends its name and standing order', (
    tester,
  ) async {
    Map<String, dynamic>? created;
    await open(tester, (method, [data = const {}]) async {
      if (method == 'supermarket.create') {
        created = data;
        return shop('Metro Fresh');
      }
      return listing([shop('Metro Fresh')]);
    });

    await tester.tap(find.text('Add supermarket'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Supermarket name'),
      'City Mart',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Address'),
      'MG Road',
    );
    await tester.tap(find.text('Add product'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Product'),
      'Dosa Batter',
    );
    await tester.enterText(find.widgetWithText(TextFormField, 'Qty'), '10');
    await tester.enterText(find.widgetWithText(TextFormField, 'Unit'), 'kg');
    await tester.tap(find.text('Save'));
    await tester.pumpAndSettle();

    expect(created, isNotNull);
    expect(created!['name'], 'City Mart');
    expect(created!['address'], 'MG Road');
    expect(created!['standing_order'], [
      {'product_name': 'Dosa Batter', 'uom': 'kg', 'planned_quantity': '10'},
    ]);
  });

  testWidgets('editing a supermarket sends its id', (tester) async {
    Map<String, dynamic>? updated;
    await open(tester, (method, [data = const {}]) async {
      if (method == 'supermarket.update') updated = data;
      return listing([shop('Metro Fresh')]);
    });

    await tester.tap(find.text('Metro Fresh'));
    await tester.pumpAndSettle();
    // The existing allocation is shown ready to change.
    expect(find.text('Idli Batter'), findsOneWidget);
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Supermarket name'),
      'Metro Fresh Kachi',
    );
    await tester.tap(find.text('Save'));
    await tester.pumpAndSettle();

    expect(updated!['id'], 1);
    expect(updated!['name'], 'Metro Fresh Kachi');
    expect(updated!['standing_order'], [
      {'product_name': 'Idli Batter', 'uom': 'packet', 'planned_quantity': '5'},
    ]);
  });

  testWidgets('a shop cannot be saved without a name', (tester) async {
    var created = false;
    await open(tester, (method, [data = const {}]) async {
      if (method == 'supermarket.create') created = true;
      return listing([]);
    });
    await tester.tap(find.text('Add supermarket'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Save'));
    await tester.pump();
    expect(created, isFalse);
    expect(find.text('Enter the name'), findsOneWidget);
  });

  testWidgets('an allocation line needs a name and a positive quantity', (
    tester,
  ) async {
    var created = false;
    await open(tester, (method, [data = const {}]) async {
      if (method == 'supermarket.create') created = true;
      return listing([]);
    });
    await tester.tap(find.text('Add supermarket'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Supermarket name'),
      'City Mart',
    );
    await tester.tap(find.text('Add product'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Product'),
      'Dosa Batter',
    );
    await tester.enterText(find.widgetWithText(TextFormField, 'Qty'), '0');
    await tester.tap(find.text('Save'));
    await tester.pump();
    expect(created, isFalse);
  });

  testWidgets('a duplicate name is reported and kept on screen', (
    tester,
  ) async {
    await open(tester, (method, [data = const {}]) async {
      if (method == 'supermarket.create') {
        throw StateError('That supermarket is already in the directory');
      }
      return listing([shop('Metro Fresh')]);
    });
    await tester.tap(find.text('Add supermarket'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Supermarket name'),
      'Metro Fresh',
    );
    await tester.tap(find.text('Save'));
    await tester.pumpAndSettle();
    expect(find.textContaining('already in the directory'), findsOneWidget);
  });

  testWidgets('a load failure can be retried', (tester) async {
    var failing = true;
    await open(tester, (method, [data = const {}]) async {
      if (failing) throw StateError('server unreachable');
      return listing([shop('Metro Fresh')]);
    });
    expect(find.textContaining('server unreachable'), findsOneWidget);
    failing = false;
    await tester.tap(find.byTooltip('Refresh supermarkets'));
    await tester.pumpAndSettle();
    expect(find.text('Metro Fresh'), findsOneWidget);
    expect(find.textContaining('server unreachable'), findsNothing);
  });
}
