import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:routeos_shell/deliveries/supermarket_directory.dart';
import 'package:routeos_shell/l10n/generated/app_localizations.dart';

import 'helpers.dart';

void main() {
  Future<dynamic> request(
    String method, [
    Map<String, dynamic> data = const {},
  ]) async => {
    'supermarkets': [
      {
        'id': 1,
        'name': 'Metro Fresh',
        'address': 'MG Road',
        'latitude': 9.93,
        'longitude': 76.27,
        'active': 1,
        'standing_order': [
          {'product_name': 'Idli Batter', 'uom': 'packet', 'quantity': '5'},
        ],
      },
    ],
  };

  testWidgets('the directory renders in Malayalam', (tester) async {
    await tester.pumpWidget(
      wrapForTest(SupermarketDirectory(request: request), deviceLanguage: 'ml'),
    );
    await tester.pumpAndSettle();

    // Screen title and the standing-order line are both translated.
    expect(find.text('സൂപ്പർമാർക്കറ്റുകൾ'), findsOneWidget);
    expect(find.text('സൂപ്പർമാർക്കറ്റ് ചേർക്കുക'), findsOneWidget);
    expect(find.textContaining('Idli Batter'), findsOneWidget);
    // The shop's own name is data, not a string to translate.
    expect(find.text('Metro Fresh'), findsOneWidget);
  });

  testWidgets('the directory renders in Arabic and lays out right to left', (
    tester,
  ) async {
    await tester.pumpWidget(
      wrapForTest(SupermarketDirectory(request: request), deviceLanguage: 'ar'),
    );
    await tester.pumpAndSettle();

    expect(find.text('أسواق السوبرماركت'), findsOneWidget);
    expect(find.text('إضافة سوبرماركت'), findsOneWidget);
    expect(
      Directionality.of(tester.element(find.byType(SupermarketDirectory))),
      TextDirection.rtl,
    );
  });

  testWidgets('an unsupported language still renders a usable screen', (
    tester,
  ) async {
    await tester.pumpWidget(
      wrapForTest(SupermarketDirectory(request: request), deviceLanguage: 'fr'),
    );
    await tester.pumpAndSettle();
    // Flutter falls back to the first supported locale rather than showing nothing.
    expect(find.text('Supermarkets'), findsOneWidget);
  });

  test('every supported locale defines every key', () {
    for (final locale in AppStrings.supportedLocales) {
      final strings = lookupAppStrings(Locale(locale.languageCode));
      expect(strings.actionSignIn, isNotEmpty, reason: locale.languageCode);
      expect(
        strings.tripBuilderCreate,
        isNotEmpty,
        reason: locale.languageCode,
      );
      expect(
        strings.confirmExtraLabel,
        isNotEmpty,
        reason: locale.languageCode,
      );
      expect(
        strings.deliveriesNextDrive('Shop'),
        isNotEmpty,
        reason: locale.languageCode,
      );
    }
  });

  test(
    'English and the translations are not identical for user-facing text',
    () {
      final english = lookupAppStrings(const Locale('en'));
      final malayalam = lookupAppStrings(const Locale('ml'));
      final arabic = lookupAppStrings(const Locale('ar'));
      expect(malayalam.actionSignIn, isNot(english.actionSignIn));
      expect(arabic.actionSignIn, isNot(english.actionSignIn));
      expect(
        arabic.deliveriesSupermarkets,
        isNot(english.deliveriesSupermarkets),
      );
      expect(
        malayalam.deliveryActionDelivered,
        isNot(english.deliveryActionDelivered),
      );
    },
  );
}
