import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_ar.dart';
import 'app_localizations_en.dart';
import 'app_localizations_ml.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppStrings
/// returned by `AppStrings.of(context)`.
///
/// Applications need to include `AppStrings.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'generated/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppStrings.localizationsDelegates,
///   supportedLocales: AppStrings.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppStrings.supportedLocales
/// property.
abstract class AppStrings {
  AppStrings(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppStrings of(BuildContext context) {
    return Localizations.of<AppStrings>(context, AppStrings)!;
  }

  static const LocalizationsDelegate<AppStrings> delegate =
      _AppStringsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('ar'),
    Locale('en'),
    Locale('ml'),
  ];

  /// Product name. Not translated.
  ///
  /// In en, this message translates to:
  /// **'RouteOS'**
  String get appTitle;

  /// No description provided for @actionSignIn.
  ///
  /// In en, this message translates to:
  /// **'Sign in'**
  String get actionSignIn;

  /// No description provided for @actionSignOut.
  ///
  /// In en, this message translates to:
  /// **'Sign out'**
  String get actionSignOut;

  /// No description provided for @actionCancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get actionCancel;

  /// No description provided for @actionConfirm.
  ///
  /// In en, this message translates to:
  /// **'Confirm'**
  String get actionConfirm;

  /// No description provided for @actionSave.
  ///
  /// In en, this message translates to:
  /// **'Save'**
  String get actionSave;

  /// No description provided for @actionRetry.
  ///
  /// In en, this message translates to:
  /// **'Retry'**
  String get actionRetry;

  /// No description provided for @actionRefresh.
  ///
  /// In en, this message translates to:
  /// **'Refresh'**
  String get actionRefresh;

  /// No description provided for @actionDelete.
  ///
  /// In en, this message translates to:
  /// **'Delete'**
  String get actionDelete;

  /// No description provided for @actionAdd.
  ///
  /// In en, this message translates to:
  /// **'Add'**
  String get actionAdd;

  /// No description provided for @actionEdit.
  ///
  /// In en, this message translates to:
  /// **'Edit'**
  String get actionEdit;

  /// No description provided for @loginTitle.
  ///
  /// In en, this message translates to:
  /// **'Sign in to RouteOS'**
  String get loginTitle;

  /// No description provided for @loginAccountName.
  ///
  /// In en, this message translates to:
  /// **'Account name'**
  String get loginAccountName;

  /// No description provided for @loginPassword.
  ///
  /// In en, this message translates to:
  /// **'Password'**
  String get loginPassword;

  /// No description provided for @loginTagline.
  ///
  /// In en, this message translates to:
  /// **'Your routes. Your road.'**
  String get loginTagline;

  /// No description provided for @loginHeadline.
  ///
  /// In en, this message translates to:
  /// **'Drive. Track. Deliver.'**
  String get loginHeadline;

  /// No description provided for @loginSigningIn.
  ///
  /// In en, this message translates to:
  /// **'Signing in… the server may take a minute to wake up.'**
  String get loginSigningIn;

  /// No description provided for @loginSessionExpired.
  ///
  /// In en, this message translates to:
  /// **'Session expired. Sign in to resume syncing.'**
  String get loginSessionExpired;

  /// No description provided for @loginNoToken.
  ///
  /// In en, this message translates to:
  /// **'Missing saved token. Sign in to resume syncing.'**
  String get loginNoToken;

  /// No description provided for @loginConfigureServer.
  ///
  /// In en, this message translates to:
  /// **'Configure server'**
  String get loginConfigureServer;

  /// No description provided for @loginServerTitle.
  ///
  /// In en, this message translates to:
  /// **'RouteOS server URL (local or HTTPS)'**
  String get loginServerTitle;

  /// No description provided for @loginServerTitleHttps.
  ///
  /// In en, this message translates to:
  /// **'RouteOS server HTTPS URL'**
  String get loginServerTitleHttps;

  /// No description provided for @loginServerConfigured.
  ///
  /// In en, this message translates to:
  /// **'Server configured.'**
  String get loginServerConfigured;

  /// No description provided for @loginSwitchAccount.
  ///
  /// In en, this message translates to:
  /// **'Switch account?'**
  String get loginSwitchAccount;

  /// No description provided for @tabHome.
  ///
  /// In en, this message translates to:
  /// **'Home'**
  String get tabHome;

  /// No description provided for @tabRoutes.
  ///
  /// In en, this message translates to:
  /// **'Routes'**
  String get tabRoutes;

  /// No description provided for @tabDraw.
  ///
  /// In en, this message translates to:
  /// **'Draw'**
  String get tabDraw;

  /// No description provided for @drawTitle.
  ///
  /// In en, this message translates to:
  /// **'Draw Route'**
  String get drawTitle;

  /// No description provided for @drawPoints.
  ///
  /// In en, this message translates to:
  /// **'{count} points · {state}'**
  String drawPoints(int count, String state);

  /// No description provided for @drawUndo.
  ///
  /// In en, this message translates to:
  /// **'Undo'**
  String get drawUndo;

  /// No description provided for @drawRedo.
  ///
  /// In en, this message translates to:
  /// **'Redo'**
  String get drawRedo;

  /// No description provided for @drawClear.
  ///
  /// In en, this message translates to:
  /// **'Clear route'**
  String get drawClear;

  /// No description provided for @drawPointsList.
  ///
  /// In en, this message translates to:
  /// **'Route points'**
  String get drawPointsList;

  /// No description provided for @drawUseMyLocation.
  ///
  /// In en, this message translates to:
  /// **'Use my location as point'**
  String get drawUseMyLocation;

  /// No description provided for @drawSave.
  ///
  /// In en, this message translates to:
  /// **'Save route'**
  String get drawSave;

  /// No description provided for @drawStart.
  ///
  /// In en, this message translates to:
  /// **'Start navigation'**
  String get drawStart;

  /// No description provided for @drawOptimize.
  ///
  /// In en, this message translates to:
  /// **'Optimize waypoint order'**
  String get drawOptimize;

  /// No description provided for @drawRecord.
  ///
  /// In en, this message translates to:
  /// **'Record route'**
  String get drawRecord;

  /// No description provided for @drawEditRoute.
  ///
  /// In en, this message translates to:
  /// **'Draw route'**
  String get drawEditRoute;

  /// No description provided for @drawMaxPoints.
  ///
  /// In en, this message translates to:
  /// **'Maximum 100 waypoints plus start and destination.'**
  String get drawMaxPoints;

  /// No description provided for @pointStart.
  ///
  /// In en, this message translates to:
  /// **'Start'**
  String get pointStart;

  /// No description provided for @pointVia.
  ///
  /// In en, this message translates to:
  /// **'Via'**
  String get pointVia;

  /// No description provided for @pointDestination.
  ///
  /// In en, this message translates to:
  /// **'Destination'**
  String get pointDestination;

  /// No description provided for @searchTitle.
  ///
  /// In en, this message translates to:
  /// **'Search destination'**
  String get searchTitle;

  /// No description provided for @searchHint.
  ///
  /// In en, this message translates to:
  /// **'Search offline places and addresses. Download the regional map for local results.'**
  String get searchHint;

  /// No description provided for @searchClear.
  ///
  /// In en, this message translates to:
  /// **'Clear search'**
  String get searchClear;

  /// No description provided for @deliveriesTitle.
  ///
  /// In en, this message translates to:
  /// **'Deliveries'**
  String get deliveriesTitle;

  /// No description provided for @deliveriesCreateTrip.
  ///
  /// In en, this message translates to:
  /// **'Create trip'**
  String get deliveriesCreateTrip;

  /// No description provided for @deliveriesAssignErp.
  ///
  /// In en, this message translates to:
  /// **'Assign ERPNext trip'**
  String get deliveriesAssignErp;

  /// No description provided for @deliveriesSyncErp.
  ///
  /// In en, this message translates to:
  /// **'Sync to ERPNext'**
  String get deliveriesSyncErp;

  /// No description provided for @deliveriesSupermarkets.
  ///
  /// In en, this message translates to:
  /// **'Supermarkets'**
  String get deliveriesSupermarkets;

  /// No description provided for @deliveriesEmpty.
  ///
  /// In en, this message translates to:
  /// **'No delivery assignments'**
  String get deliveriesEmpty;

  /// No description provided for @deliveriesEmptyHint.
  ///
  /// In en, this message translates to:
  /// **'An admin can create a trip here, or import an ERPNext delivery trip. Drivers only see their own assignments.'**
  String get deliveriesEmptyHint;

  /// No description provided for @deliveriesLinkRide.
  ///
  /// In en, this message translates to:
  /// **'Link my current ride'**
  String get deliveriesLinkRide;

  /// No description provided for @deliveriesMoveBatter.
  ///
  /// In en, this message translates to:
  /// **'Move between shops'**
  String get deliveriesMoveBatter;

  /// No description provided for @deliveriesStillToHandOver.
  ///
  /// In en, this message translates to:
  /// **'Still to hand over: {items}'**
  String deliveriesStillToHandOver(String items);

  /// No description provided for @deliveriesAssignProducts.
  ///
  /// In en, this message translates to:
  /// **'Assign products'**
  String get deliveriesAssignProducts;

  /// No description provided for @deliveriesExtraTitle.
  ///
  /// In en, this message translates to:
  /// **'Extra requested by shops'**
  String get deliveriesExtraTitle;

  /// No description provided for @deliveriesExtraHint.
  ///
  /// In en, this message translates to:
  /// **'Drivers handed over only the plan. Build these into a later trip, or give them to another shop so nothing is left over.'**
  String get deliveriesExtraHint;

  /// No description provided for @deliveriesExtraRecorded.
  ///
  /// In en, this message translates to:
  /// **'Recorded once'**
  String get deliveriesExtraRecorded;

  /// No description provided for @deliveriesExtraRecordedMany.
  ///
  /// In en, this message translates to:
  /// **'Recorded {count} times'**
  String deliveriesExtraRecordedMany(int count);

  /// No description provided for @deliveriesExtraPlanned.
  ///
  /// In en, this message translates to:
  /// **'Planned'**
  String get deliveriesExtraPlanned;

  /// No description provided for @deliveriesExtraResolved.
  ///
  /// In en, this message translates to:
  /// **'{shop} no longer waiting on {amount} {unit} {product}.'**
  String deliveriesExtraResolved(
    String shop,
    String amount,
    String unit,
    String product,
  );

  /// No description provided for @confirmTitleDelivered.
  ///
  /// In en, this message translates to:
  /// **'Confirm delivered?'**
  String get confirmTitleDelivered;

  /// No description provided for @confirmTitlePartial.
  ///
  /// In en, this message translates to:
  /// **'Record partial delivery?'**
  String get confirmTitlePartial;

  /// No description provided for @confirmTitleFailed.
  ///
  /// In en, this message translates to:
  /// **'Record failed delivery?'**
  String get confirmTitleFailed;

  /// No description provided for @confirmTitleArrived.
  ///
  /// In en, this message translates to:
  /// **'Record arrival?'**
  String get confirmTitleArrived;

  /// No description provided for @confirmGpsNote.
  ///
  /// In en, this message translates to:
  /// **'GPS arrival alone does not confirm delivery. Final outcomes cannot be overwritten.'**
  String get confirmGpsNote;

  /// No description provided for @confirmNoProducts.
  ///
  /// In en, this message translates to:
  /// **'No products assigned. Ask the admin to add the products and quantities first.'**
  String get confirmNoProducts;

  /// No description provided for @confirmDeliveredLabel.
  ///
  /// In en, this message translates to:
  /// **'{product} delivered ({unit})'**
  String confirmDeliveredLabel(String product, String unit);

  /// No description provided for @confirmAssigned.
  ///
  /// In en, this message translates to:
  /// **'Assigned: {quantity} {unit}'**
  String confirmAssigned(String quantity, String unit);

  /// No description provided for @confirmExtraLabel.
  ///
  /// In en, this message translates to:
  /// **'Extra this shop asked for next trip'**
  String get confirmExtraLabel;

  /// No description provided for @confirmExtraHint.
  ///
  /// In en, this message translates to:
  /// **'Recorded only. Nothing extra is handed over now.'**
  String get confirmExtraHint;

  /// No description provided for @confirmExtraPositive.
  ///
  /// In en, this message translates to:
  /// **'Enter a positive quantity with up to 3 decimals'**
  String get confirmExtraPositive;

  /// No description provided for @confirmPartialReason.
  ///
  /// In en, this message translates to:
  /// **'Reason for shortage'**
  String get confirmPartialReason;

  /// No description provided for @confirmFailedReason.
  ///
  /// In en, this message translates to:
  /// **'Why did delivery fail?'**
  String get confirmFailedReason;

  /// No description provided for @confirmReasonRequired.
  ///
  /// In en, this message translates to:
  /// **'A reason is required'**
  String get confirmReasonRequired;

  /// No description provided for @confirmUsePartial.
  ///
  /// In en, this message translates to:
  /// **'For a shortage, cancel and choose partial delivery'**
  String get confirmUsePartial;

  /// No description provided for @confirmQuantityRange.
  ///
  /// In en, this message translates to:
  /// **'Enter 0 to {planned}, with up to 3 decimal places'**
  String confirmQuantityRange(String planned);

  /// No description provided for @confirmDeliveredSummary.
  ///
  /// In en, this message translates to:
  /// **'{product}: {delivered} / {planned} {unit} delivered'**
  String confirmDeliveredSummary(
    String product,
    String delivered,
    String planned,
    String unit,
  );

  /// No description provided for @tripBuilderTitle.
  ///
  /// In en, this message translates to:
  /// **'Create trip'**
  String get tripBuilderTitle;

  /// No description provided for @tripBuilderReference.
  ///
  /// In en, this message translates to:
  /// **'Trip reference'**
  String get tripBuilderReference;

  /// No description provided for @tripBuilderReferenceHint.
  ///
  /// In en, this message translates to:
  /// **'For example SAP-TRIP-1042. Reusing it never duplicates a trip.'**
  String get tripBuilderReferenceHint;

  /// No description provided for @tripBuilderDriver.
  ///
  /// In en, this message translates to:
  /// **'Driver'**
  String get tripBuilderDriver;

  /// No description provided for @tripBuilderVehicle.
  ///
  /// In en, this message translates to:
  /// **'Vehicle number'**
  String get tripBuilderVehicle;

  /// No description provided for @tripBuilderVehicleHint.
  ///
  /// In en, this message translates to:
  /// **'The driver must start their ride with this exact vehicle.'**
  String get tripBuilderVehicleHint;

  /// No description provided for @tripBuilderSupermarkets.
  ///
  /// In en, this message translates to:
  /// **'Supermarkets'**
  String get tripBuilderSupermarkets;

  /// No description provided for @tripBuilderAddSupermarket.
  ///
  /// In en, this message translates to:
  /// **'Add supermarket'**
  String get tripBuilderAddSupermarket;

  /// No description provided for @tripBuilderStopTitle.
  ///
  /// In en, this message translates to:
  /// **'Supermarket {number}'**
  String tripBuilderStopTitle(int number);

  /// No description provided for @tripBuilderShopName.
  ///
  /// In en, this message translates to:
  /// **'Supermarket name'**
  String get tripBuilderShopName;

  /// No description provided for @tripBuilderAddress.
  ///
  /// In en, this message translates to:
  /// **'Address'**
  String get tripBuilderAddress;

  /// No description provided for @tripBuilderLatitude.
  ///
  /// In en, this message translates to:
  /// **'Latitude'**
  String get tripBuilderLatitude;

  /// No description provided for @tripBuilderLongitude.
  ///
  /// In en, this message translates to:
  /// **'Longitude'**
  String get tripBuilderLongitude;

  /// No description provided for @tripBuilderProducts.
  ///
  /// In en, this message translates to:
  /// **'Products to deliver'**
  String get tripBuilderProducts;

  /// No description provided for @tripBuilderAddProduct.
  ///
  /// In en, this message translates to:
  /// **'Add product'**
  String get tripBuilderAddProduct;

  /// No description provided for @tripBuilderRemoveProduct.
  ///
  /// In en, this message translates to:
  /// **'Remove product'**
  String get tripBuilderRemoveProduct;

  /// No description provided for @tripBuilderProduct.
  ///
  /// In en, this message translates to:
  /// **'Product'**
  String get tripBuilderProduct;

  /// No description provided for @tripBuilderQuantity.
  ///
  /// In en, this message translates to:
  /// **'Qty'**
  String get tripBuilderQuantity;

  /// No description provided for @tripBuilderUnit.
  ///
  /// In en, this message translates to:
  /// **'Unit'**
  String get tripBuilderUnit;

  /// No description provided for @tripBuilderSaveStop.
  ///
  /// In en, this message translates to:
  /// **'Save stop'**
  String get tripBuilderSaveStop;

  /// No description provided for @tripBuilderStopNeedsProduct.
  ///
  /// In en, this message translates to:
  /// **'Add at least one product so the driver can confirm the delivery'**
  String get tripBuilderStopNeedsProduct;

  /// No description provided for @tripBuilderProductIncomplete.
  ///
  /// In en, this message translates to:
  /// **'Each product needs a name, a positive quantity and a unit'**
  String get tripBuilderProductIncomplete;

  /// No description provided for @tripBuilderStopWithoutProducts.
  ///
  /// In en, this message translates to:
  /// **'Every supermarket needs at least one product and quantity, otherwise the driver cannot confirm the delivery.'**
  String get tripBuilderStopWithoutProducts;

  /// No description provided for @tripBuilderCreate.
  ///
  /// In en, this message translates to:
  /// **'Create trip'**
  String get tripBuilderCreate;

  /// No description provided for @tripBuilderCreated.
  ///
  /// In en, this message translates to:
  /// **'Trip created and assigned to the driver.'**
  String get tripBuilderCreated;

  /// No description provided for @tripBuilderCoordinateRange.
  ///
  /// In en, this message translates to:
  /// **'Out of range'**
  String get tripBuilderCoordinateRange;

  /// No description provided for @tripBuilderCoordinateMissing.
  ///
  /// In en, this message translates to:
  /// **'Enter a coordinate'**
  String get tripBuilderCoordinateMissing;

  /// No description provided for @tripBuilderTripSaved.
  ///
  /// In en, this message translates to:
  /// **'Trip created and assigned to the driver.'**
  String get tripBuilderTripSaved;

  /// No description provided for @transferTitle.
  ///
  /// In en, this message translates to:
  /// **'Move batter between shops'**
  String get transferTitle;

  /// No description provided for @transferHint.
  ///
  /// In en, this message translates to:
  /// **'Batter a shop will not take can go to another shop on this trip instead of being left over. The driver still hands over only the plan.'**
  String get transferHint;

  /// No description provided for @transferFrom.
  ///
  /// In en, this message translates to:
  /// **'Take from'**
  String get transferFrom;

  /// No description provided for @transferTo.
  ///
  /// In en, this message translates to:
  /// **'Give to'**
  String get transferTo;

  /// No description provided for @transferProduct.
  ///
  /// In en, this message translates to:
  /// **'Product'**
  String get transferProduct;

  /// No description provided for @transferProductOption.
  ///
  /// In en, this message translates to:
  /// **'{product} (planned {planned} {unit})'**
  String transferProductOption(String product, String planned, String unit);

  /// No description provided for @transferQuantity.
  ///
  /// In en, this message translates to:
  /// **'How much to move ({unit})'**
  String transferQuantity(String unit);

  /// No description provided for @transferMove.
  ///
  /// In en, this message translates to:
  /// **'Move'**
  String get transferMove;

  /// No description provided for @transferPositive.
  ///
  /// In en, this message translates to:
  /// **'Enter a positive quantity'**
  String get transferPositive;

  /// No description provided for @transferNeedsTwoStops.
  ///
  /// In en, this message translates to:
  /// **'Add at least two unconfirmed shops before moving batter.'**
  String get transferNeedsTwoStops;

  /// No description provided for @shopTitle.
  ///
  /// In en, this message translates to:
  /// **'Supermarkets'**
  String get shopTitle;

  /// No description provided for @shopAdd.
  ///
  /// In en, this message translates to:
  /// **'Add supermarket'**
  String get shopAdd;

  /// No description provided for @shopEdit.
  ///
  /// In en, this message translates to:
  /// **'Edit supermarket'**
  String get shopEdit;

  /// No description provided for @shopName.
  ///
  /// In en, this message translates to:
  /// **'Supermarket name'**
  String get shopName;

  /// No description provided for @shopAddress.
  ///
  /// In en, this message translates to:
  /// **'Address'**
  String get shopAddress;

  /// No description provided for @shopLatitude.
  ///
  /// In en, this message translates to:
  /// **'Latitude'**
  String get shopLatitude;

  /// No description provided for @shopLongitude.
  ///
  /// In en, this message translates to:
  /// **'Longitude'**
  String get shopLongitude;

  /// No description provided for @shopUsualOrder.
  ///
  /// In en, this message translates to:
  /// **'Usual allocation'**
  String get shopUsualOrder;

  /// No description provided for @shopUsualOrderHint.
  ///
  /// In en, this message translates to:
  /// **'Applied automatically when a trip includes this shop. Leave empty if the shop does not take a fixed amount.'**
  String get shopUsualOrderHint;

  /// No description provided for @shopInactive.
  ///
  /// In en, this message translates to:
  /// **'Inactive'**
  String get shopInactive;

  /// No description provided for @shopNoOrder.
  ///
  /// In en, this message translates to:
  /// **'No usual allocation yet'**
  String get shopNoOrder;

  /// No description provided for @shopOrderSummary.
  ///
  /// In en, this message translates to:
  /// **'{quantity} {unit} {product}'**
  String shopOrderSummary(String quantity, String unit, String product);

  /// No description provided for @shopProductIncomplete.
  ///
  /// In en, this message translates to:
  /// **'Each product needs a name, a positive quantity and a unit'**
  String get shopProductIncomplete;

  /// No description provided for @shopNameRequired.
  ///
  /// In en, this message translates to:
  /// **'Enter the name'**
  String get shopNameRequired;

  /// No description provided for @adminActiveDrivers.
  ///
  /// In en, this message translates to:
  /// **'Active drivers'**
  String get adminActiveDrivers;

  /// No description provided for @adminLiveRides.
  ///
  /// In en, this message translates to:
  /// **'{count} live rides'**
  String adminLiveRides(int count);

  /// No description provided for @adminNoRides.
  ///
  /// In en, this message translates to:
  /// **'No active rides'**
  String get adminNoRides;

  /// No description provided for @adminNoRidesHint.
  ///
  /// In en, this message translates to:
  /// **'Drivers appear here when they start a ride.'**
  String get adminNoRidesHint;

  /// No description provided for @stateStart.
  ///
  /// In en, this message translates to:
  /// **'Start'**
  String get stateStart;

  /// No description provided for @stateVia.
  ///
  /// In en, this message translates to:
  /// **'Via'**
  String get stateVia;

  /// No description provided for @stateDestination.
  ///
  /// In en, this message translates to:
  /// **'Destination'**
  String get stateDestination;

  /// No description provided for @statePending.
  ///
  /// In en, this message translates to:
  /// **'Pending'**
  String get statePending;

  /// No description provided for @stateArrived.
  ///
  /// In en, this message translates to:
  /// **'Arrived'**
  String get stateArrived;

  /// No description provided for @stateDelivered.
  ///
  /// In en, this message translates to:
  /// **'Delivered'**
  String get stateDelivered;

  /// No description provided for @statePartial.
  ///
  /// In en, this message translates to:
  /// **'Partial'**
  String get statePartial;

  /// No description provided for @stateFailed.
  ///
  /// In en, this message translates to:
  /// **'Failed'**
  String get stateFailed;

  /// No description provided for @deliveriesErpEmpty.
  ///
  /// In en, this message translates to:
  /// **'Create a submitted delivery trip with a driver in ERPNext, and a driver account in RouteOS, first.'**
  String get deliveriesErpEmpty;

  /// No description provided for @deliveriesAssignErpTitle.
  ///
  /// In en, this message translates to:
  /// **'Assign ERPNext delivery'**
  String get deliveriesAssignErpTitle;

  /// No description provided for @deliveriesMatchingDriver.
  ///
  /// In en, this message translates to:
  /// **'Matching RouteOS driver'**
  String get deliveriesMatchingDriver;

  /// No description provided for @deliveriesDriverWarning.
  ///
  /// In en, this message translates to:
  /// **'Check the driver carefully. This links their accounts; existing delivery confirmations will not be reset.'**
  String get deliveriesDriverWarning;

  /// No description provided for @deliveriesExtraNote.
  ///
  /// In en, this message translates to:
  /// **'Planned into a later trip'**
  String get deliveriesExtraNote;

  /// No description provided for @deliveriesAssignProductsTitle.
  ///
  /// In en, this message translates to:
  /// **'Assign products and quantities'**
  String get deliveriesAssignProductsTitle;

  /// No description provided for @deliveriesAssignHint.
  ///
  /// In en, this message translates to:
  /// **'Examples: Milk in litres, Batter in kg, Curd in packets. Use the same unit when the driver confirms delivery.'**
  String get deliveriesAssignHint;

  /// No description provided for @deliveriesUnitLabel.
  ///
  /// In en, this message translates to:
  /// **'Unit (L, kg, packets, etc.)'**
  String get deliveriesUnitLabel;

  /// No description provided for @deliveriesRemoveLast.
  ///
  /// In en, this message translates to:
  /// **'Remove last product'**
  String get deliveriesRemoveLast;

  /// No description provided for @deliveriesSyncQueued.
  ///
  /// In en, this message translates to:
  /// **'Sync queued. It runs within 30 seconds; refresh to see the result.'**
  String get deliveriesSyncQueued;

  /// No description provided for @deliveriesSyncBusy.
  ///
  /// In en, this message translates to:
  /// **'Sync is already running.'**
  String get deliveriesSyncBusy;

  /// No description provided for @deliveriesSyncCounts.
  ///
  /// In en, this message translates to:
  /// **'{synced} synced, {failed} failed. Failed updates are kept for retry.'**
  String deliveriesSyncCounts(int synced, int failed);

  /// No description provided for @deliveriesLastGps.
  ///
  /// In en, this message translates to:
  /// **'Last GPS: {latitude}, {longitude}'**
  String deliveriesLastGps(String latitude, String longitude);

  /// No description provided for @deliveriesRecordedAt.
  ///
  /// In en, this message translates to:
  /// **'Recorded: {time}'**
  String deliveriesRecordedAt(String time);

  /// No description provided for @deliveriesRide.
  ///
  /// In en, this message translates to:
  /// **'Ride: {status}'**
  String deliveriesRide(String status);

  /// No description provided for @deliveriesLinkHint.
  ///
  /// In en, this message translates to:
  /// **'Driver: start a saved route using the ERP vehicle number, then link the ride here.'**
  String get deliveriesLinkHint;

  /// No description provided for @deliveriesNote.
  ///
  /// In en, this message translates to:
  /// **'Delivery Note: {note}'**
  String deliveriesNote(String note);

  /// No description provided for @deliveriesGpsNote.
  ///
  /// In en, this message translates to:
  /// **'GPS arrival alone does not confirm delivery. Final outcomes cannot be overwritten.'**
  String get deliveriesGpsNote;

  /// No description provided for @tripBuilderCreateFailed.
  ///
  /// In en, this message translates to:
  /// **'Could not create the trip: {error}'**
  String tripBuilderCreateFailed(String error);

  /// No description provided for @tripBuilderTripReferenceRequired.
  ///
  /// In en, this message translates to:
  /// **'Enter a trip reference'**
  String get tripBuilderTripReferenceRequired;

  /// No description provided for @tripBuilderVehicleRequired.
  ///
  /// In en, this message translates to:
  /// **'Enter the vehicle number'**
  String get tripBuilderVehicleRequired;

  /// No description provided for @deliveriesRefresh.
  ///
  /// In en, this message translates to:
  /// **'Refresh deliveries'**
  String get deliveriesRefresh;

  /// No description provided for @shopRefresh.
  ///
  /// In en, this message translates to:
  /// **'Refresh supermarkets'**
  String get shopRefresh;

  /// No description provided for @tabAccount.
  ///
  /// In en, this message translates to:
  /// **'Account'**
  String get tabAccount;

  /// No description provided for @routesFilterAll.
  ///
  /// In en, this message translates to:
  /// **'All'**
  String get routesFilterAll;

  /// No description provided for @routesTitle.
  ///
  /// In en, this message translates to:
  /// **'My Routes'**
  String get routesTitle;

  /// No description provided for @routesSavedTitle.
  ///
  /// In en, this message translates to:
  /// **'Saved Routes'**
  String get routesSavedTitle;

  /// No description provided for @routesEmpty.
  ///
  /// In en, this message translates to:
  /// **'No saved routes yet. Plan or record your first route.'**
  String get routesEmpty;

  /// No description provided for @routesSearch.
  ///
  /// In en, this message translates to:
  /// **'Search saved routes'**
  String get routesSearch;

  /// No description provided for @routesFavourites.
  ///
  /// In en, this message translates to:
  /// **'Favourites'**
  String get routesFavourites;

  /// No description provided for @routesRemoveRecent.
  ///
  /// In en, this message translates to:
  /// **'Remove from recent routes'**
  String get routesRemoveRecent;

  /// No description provided for @routeCalculateFailed.
  ///
  /// In en, this message translates to:
  /// **'Could not calculate this route. Check offline map coverage and retry.'**
  String get routeCalculateFailed;

  /// No description provided for @routeLoadFailed.
  ///
  /// In en, this message translates to:
  /// **'Could not load this route. Check your connection and retry.'**
  String get routeLoadFailed;

  /// No description provided for @routeTimeout.
  ///
  /// In en, this message translates to:
  /// **'Route calculation timed out. Check regional maps and retry.'**
  String get routeTimeout;

  /// No description provided for @routeName.
  ///
  /// In en, this message translates to:
  /// **'Route name'**
  String get routeName;

  /// No description provided for @routeDelete.
  ///
  /// In en, this message translates to:
  /// **'Delete route'**
  String get routeDelete;

  /// No description provided for @routeRename.
  ///
  /// In en, this message translates to:
  /// **'Rename route'**
  String get routeRename;

  /// No description provided for @routeShare.
  ///
  /// In en, this message translates to:
  /// **'Share route'**
  String get routeShare;

  /// No description provided for @routeOpen.
  ///
  /// In en, this message translates to:
  /// **'Open / edit drawn route'**
  String get routeOpen;

  /// No description provided for @routeFollow.
  ///
  /// In en, this message translates to:
  /// **'Follow the route'**
  String get routeFollow;

  /// No description provided for @routeFavouriteToggle.
  ///
  /// In en, this message translates to:
  /// **'Toggle favourite'**
  String get routeFavouriteToggle;

  /// No description provided for @routeSaved.
  ///
  /// In en, this message translates to:
  /// **'Route saved and available to other drivers.'**
  String get routeSaved;

  /// No description provided for @routeShared.
  ///
  /// In en, this message translates to:
  /// **'Route shared with RouteOS drivers.'**
  String get routeShared;

  /// No description provided for @drawOptimizeTitle.
  ///
  /// In en, this message translates to:
  /// **'Optimize waypoint order?'**
  String get drawOptimizeTitle;

  /// No description provided for @drawOrganicsLimit.
  ///
  /// In en, this message translates to:
  /// **'Organic Maps supports 100 waypoints plus start and destination.'**
  String get drawOrganicsLimit;

  /// No description provided for @drawDriverOnly.
  ///
  /// In en, this message translates to:
  /// **'Route drawing is available to drivers only.'**
  String get drawDriverOnly;

  /// No description provided for @drawMaxPointsReached.
  ///
  /// In en, this message translates to:
  /// **'Maximum 102 route points reached.'**
  String get drawMaxPointsReached;

  /// No description provided for @pointDelete.
  ///
  /// In en, this message translates to:
  /// **'Delete point'**
  String get pointDelete;

  /// No description provided for @pointInsertAfter.
  ///
  /// In en, this message translates to:
  /// **'Insert after'**
  String get pointInsertAfter;

  /// No description provided for @pointMoveOnMap.
  ///
  /// In en, this message translates to:
  /// **'Move on map'**
  String get pointMoveOnMap;

  /// No description provided for @pointMoveEarlier.
  ///
  /// In en, this message translates to:
  /// **'Move earlier'**
  String get pointMoveEarlier;

  /// No description provided for @pointMoveLater.
  ///
  /// In en, this message translates to:
  /// **'Move later'**
  String get pointMoveLater;

  /// No description provided for @pointMoveTap.
  ///
  /// In en, this message translates to:
  /// **'Tap the new position for point'**
  String get pointMoveTap;

  /// No description provided for @pointInsertTap.
  ///
  /// In en, this message translates to:
  /// **'Tap to insert a point'**
  String get pointInsertTap;

  /// No description provided for @pointEdit.
  ///
  /// In en, this message translates to:
  /// **'Edit point'**
  String get pointEdit;

  /// No description provided for @pointLabel.
  ///
  /// In en, this message translates to:
  /// **'Point {number} · {type}'**
  String pointLabel(int number, String type);

  /// No description provided for @mapMyLocation.
  ///
  /// In en, this message translates to:
  /// **'My location'**
  String get mapMyLocation;

  /// No description provided for @mapZoomIn.
  ///
  /// In en, this message translates to:
  /// **'Zoom in'**
  String get mapZoomIn;

  /// No description provided for @mapZoomOut.
  ///
  /// In en, this message translates to:
  /// **'Zoom out'**
  String get mapZoomOut;

  /// No description provided for @mapDownloads.
  ///
  /// In en, this message translates to:
  /// **'Offline maps'**
  String get mapDownloads;

  /// No description provided for @searchPlaces.
  ///
  /// In en, this message translates to:
  /// **'Search places'**
  String get searchPlaces;

  /// No description provided for @vehicleSelect.
  ///
  /// In en, this message translates to:
  /// **'Select vehicle'**
  String get vehicleSelect;

  /// No description provided for @rideStart.
  ///
  /// In en, this message translates to:
  /// **'Start ride'**
  String get rideStart;

  /// No description provided for @rideEnd.
  ///
  /// In en, this message translates to:
  /// **'End ride'**
  String get rideEnd;

  /// No description provided for @rideEndTitle.
  ///
  /// In en, this message translates to:
  /// **'End this ride?'**
  String get rideEndTitle;

  /// No description provided for @rideWaitingGps.
  ///
  /// In en, this message translates to:
  /// **'Ride active — waiting for GPS'**
  String get rideWaitingGps;

  /// No description provided for @rideWaitingGuidance.
  ///
  /// In en, this message translates to:
  /// **'Waiting for GPS guidance'**
  String get rideWaitingGuidance;

  /// No description provided for @rideStarting.
  ///
  /// In en, this message translates to:
  /// **'Starting navigation — please wait.'**
  String get rideStarting;

  /// No description provided for @rideLiveTrackingNote.
  ///
  /// In en, this message translates to:
  /// **'Live tracking stops after RouteOS confirms the ride has ended.'**
  String get rideLiveTrackingNote;

  /// No description provided for @rideLoadPrompt.
  ///
  /// In en, this message translates to:
  /// **'Load route, choose a vehicle, and start navigation'**
  String get rideLoadPrompt;

  /// No description provided for @rideLocationMissing.
  ///
  /// In en, this message translates to:
  /// **'not received'**
  String get rideLocationMissing;

  /// No description provided for @rideEndNavigationFirst.
  ///
  /// In en, this message translates to:
  /// **'End navigation before editing a route.'**
  String get rideEndNavigationFirst;

  /// No description provided for @recordStopSave.
  ///
  /// In en, this message translates to:
  /// **'Stop & save'**
  String get recordStopSave;

  /// No description provided for @recordDiscard.
  ///
  /// In en, this message translates to:
  /// **'Discard'**
  String get recordDiscard;

  /// No description provided for @recordDiscardTitle.
  ///
  /// In en, this message translates to:
  /// **'Discard recording?'**
  String get recordDiscardTitle;

  /// No description provided for @recordStopFirst.
  ///
  /// In en, this message translates to:
  /// **'Stop or discard the recording first.'**
  String get recordStopFirst;

  /// No description provided for @recordDiscardHint.
  ///
  /// In en, this message translates to:
  /// **'Stop the native recorder and discard the unsaved track.'**
  String get recordDiscardHint;

  /// No description provided for @recordSeparateNote.
  ///
  /// In en, this message translates to:
  /// **'Original GPS track is kept separate from drawn routes.'**
  String get recordSeparateNote;

  /// No description provided for @recordProgress.
  ///
  /// In en, this message translates to:
  /// **'Recording Route · {distance}'**
  String recordProgress(String distance);

  /// No description provided for @sessionRestoreFailed.
  ///
  /// In en, this message translates to:
  /// **'Could not restore your session: {error}'**
  String sessionRestoreFailed(String error);

  /// No description provided for @screenClosed.
  ///
  /// In en, this message translates to:
  /// **'Screen closed'**
  String get screenClosed;

  /// No description provided for @loginDevelopmentAccounts.
  ///
  /// In en, this message translates to:
  /// **'Development accounts'**
  String get loginDevelopmentAccounts;

  /// No description provided for @actionRename.
  ///
  /// In en, this message translates to:
  /// **'Rename'**
  String get actionRename;

  /// No description provided for @adminRefreshRides.
  ///
  /// In en, this message translates to:
  /// **'Refresh live rides'**
  String get adminRefreshRides;
}

class _AppStringsDelegate extends LocalizationsDelegate<AppStrings> {
  const _AppStringsDelegate();

  @override
  Future<AppStrings> load(Locale locale) {
    return SynchronousFuture<AppStrings>(lookupAppStrings(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['ar', 'en', 'ml'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppStringsDelegate old) => false;
}

AppStrings lookupAppStrings(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'ar':
      return AppStringsAr();
    case 'en':
      return AppStringsEn();
    case 'ml':
      return AppStringsMl();
  }

  throw FlutterError(
    'AppStrings.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
