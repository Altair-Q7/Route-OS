// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppStringsEn extends AppStrings {
  AppStringsEn([String locale = 'en']) : super(locale);

  @override
  String get appTitle => 'RouteOS';

  @override
  String get actionSignIn => 'Sign in';

  @override
  String get actionSignOut => 'Sign out';

  @override
  String get actionCancel => 'Cancel';

  @override
  String get actionConfirm => 'Confirm';

  @override
  String get actionSave => 'Save';

  @override
  String get actionRetry => 'Retry';

  @override
  String get actionRefresh => 'Refresh';

  @override
  String get actionDelete => 'Delete';

  @override
  String get actionAdd => 'Add';

  @override
  String get actionEdit => 'Edit';

  @override
  String get loginTitle => 'Sign in to RouteOS';

  @override
  String get loginAccountName => 'Account name';

  @override
  String get loginPassword => 'Password';

  @override
  String get loginTagline => 'Your routes. Your road.';

  @override
  String get loginHeadline => 'Drive. Track. Deliver.';

  @override
  String get loginSigningIn =>
      'Signing in… the server may take a minute to wake up.';

  @override
  String get loginSessionExpired =>
      'Session expired. Sign in to resume syncing.';

  @override
  String get loginNoToken => 'Missing saved token. Sign in to resume syncing.';

  @override
  String get loginConfigureServer => 'Configure server';

  @override
  String get loginServerTitle => 'RouteOS server URL (local or HTTPS)';

  @override
  String get loginServerTitleHttps => 'RouteOS server HTTPS URL';

  @override
  String get loginServerConfigured => 'Server configured.';

  @override
  String get loginSwitchAccount => 'Switch account?';

  @override
  String get tabHome => 'Home';

  @override
  String get tabRoutes => 'Routes';

  @override
  String get tabDraw => 'Draw';

  @override
  String get drawTitle => 'Draw Route';

  @override
  String drawPoints(int count, String state) {
    return '$count points · $state';
  }

  @override
  String get drawUndo => 'Undo';

  @override
  String get drawRedo => 'Redo';

  @override
  String get drawClear => 'Clear route';

  @override
  String get drawPointsList => 'Route points';

  @override
  String get drawUseMyLocation => 'Use my location as point';

  @override
  String get drawSave => 'Save route';

  @override
  String get drawStart => 'Start navigation';

  @override
  String get drawOptimize => 'Optimize waypoint order';

  @override
  String get drawRecord => 'Record route';

  @override
  String get drawEditRoute => 'Draw route';

  @override
  String get drawMaxPoints =>
      'Maximum 100 waypoints plus start and destination.';

  @override
  String get pointStart => 'Start';

  @override
  String get pointVia => 'Via';

  @override
  String get pointDestination => 'Destination';

  @override
  String get searchTitle => 'Search destination';

  @override
  String get searchHint =>
      'Search offline places and addresses. Download the regional map for local results.';

  @override
  String get searchClear => 'Clear search';

  @override
  String get deliveriesTitle => 'Deliveries';

  @override
  String get deliveriesCreateTrip => 'Create trip';

  @override
  String get deliveriesAssignErp => 'Assign ERPNext trip';

  @override
  String get deliveriesSyncErp => 'Sync to ERPNext';

  @override
  String get deliveriesSupermarkets => 'Supermarkets';

  @override
  String get deliveriesEmpty => 'No delivery assignments';

  @override
  String get deliveriesEmptyHint =>
      'An admin can create a trip here, or import an ERPNext delivery trip. Drivers only see their own assignments.';

  @override
  String get deliveriesLinkRide => 'Link my current ride';

  @override
  String get deliveriesMoveBatter => 'Move between shops';

  @override
  String deliveriesStillToHandOver(String items) {
    return 'Still to hand over: $items';
  }

  @override
  String get deliveriesAssignProducts => 'Assign products';

  @override
  String get deliveriesExtraTitle => 'Extra requested by shops';

  @override
  String get deliveriesExtraHint =>
      'Drivers handed over only the plan. Build these into a later trip, or give them to another shop so nothing is left over.';

  @override
  String get deliveriesExtraRecorded => 'Recorded once';

  @override
  String deliveriesExtraRecordedMany(int count) {
    return 'Recorded $count times';
  }

  @override
  String get deliveriesExtraPlanned => 'Planned';

  @override
  String deliveriesExtraResolved(
    String shop,
    String amount,
    String unit,
    String product,
  ) {
    return '$shop no longer waiting on $amount $unit $product.';
  }

  @override
  String get confirmTitleDelivered => 'Confirm delivered?';

  @override
  String get confirmTitlePartial => 'Record partial delivery?';

  @override
  String get confirmTitleFailed => 'Record failed delivery?';

  @override
  String get confirmTitleArrived => 'Record arrival?';

  @override
  String get confirmGpsNote =>
      'GPS arrival alone does not confirm delivery. Final outcomes cannot be overwritten.';

  @override
  String get confirmNoProducts =>
      'No products assigned. Ask the admin to add the products and quantities first.';

  @override
  String confirmDeliveredLabel(String product, String unit) {
    return '$product delivered ($unit)';
  }

  @override
  String confirmAssigned(String quantity, String unit) {
    return 'Assigned: $quantity $unit';
  }

  @override
  String get confirmExtraLabel => 'Extra this shop asked for next trip';

  @override
  String get confirmExtraHint =>
      'Recorded only. Nothing extra is handed over now.';

  @override
  String get confirmExtraPositive =>
      'Enter a positive quantity with up to 3 decimals';

  @override
  String get confirmPartialReason => 'Reason for shortage';

  @override
  String get confirmFailedReason => 'Why did delivery fail?';

  @override
  String get confirmReasonRequired => 'A reason is required';

  @override
  String get confirmUsePartial =>
      'For a shortage, cancel and choose partial delivery';

  @override
  String confirmQuantityRange(String planned) {
    return 'Enter 0 to $planned, with up to 3 decimal places';
  }

  @override
  String confirmDeliveredSummary(
    String product,
    String delivered,
    String planned,
    String unit,
  ) {
    return '$product: $delivered / $planned $unit delivered';
  }

  @override
  String get tripBuilderTitle => 'Create trip';

  @override
  String get tripBuilderReference => 'Trip reference';

  @override
  String get tripBuilderReferenceHint =>
      'For example SAP-TRIP-1042. Reusing it never duplicates a trip.';

  @override
  String get tripBuilderDriver => 'Driver';

  @override
  String get tripBuilderVehicle => 'Vehicle number';

  @override
  String get tripBuilderVehicleHint =>
      'The driver must start their ride with this exact vehicle.';

  @override
  String get tripBuilderSupermarkets => 'Supermarkets';

  @override
  String get tripBuilderAddSupermarket => 'Add supermarket';

  @override
  String tripBuilderStopTitle(int number) {
    return 'Supermarket $number';
  }

  @override
  String get tripBuilderShopName => 'Supermarket name';

  @override
  String get tripBuilderAddress => 'Address';

  @override
  String get tripBuilderLatitude => 'Latitude';

  @override
  String get tripBuilderLongitude => 'Longitude';

  @override
  String get tripBuilderProducts => 'Products to deliver';

  @override
  String get tripBuilderAddProduct => 'Add product';

  @override
  String get tripBuilderRemoveProduct => 'Remove product';

  @override
  String get tripBuilderProduct => 'Product';

  @override
  String get tripBuilderQuantity => 'Qty';

  @override
  String get tripBuilderUnit => 'Unit';

  @override
  String get tripBuilderSaveStop => 'Save stop';

  @override
  String get tripBuilderStopNeedsProduct =>
      'Add at least one product so the driver can confirm the delivery';

  @override
  String get tripBuilderProductIncomplete =>
      'Each product needs a name, a positive quantity and a unit';

  @override
  String get tripBuilderStopWithoutProducts =>
      'Every supermarket needs at least one product and quantity, otherwise the driver cannot confirm the delivery.';

  @override
  String get tripBuilderCreate => 'Create trip';

  @override
  String get tripBuilderCreated => 'Trip created and assigned to the driver.';

  @override
  String get tripBuilderCoordinateRange => 'Out of range';

  @override
  String get tripBuilderCoordinateMissing => 'Enter a coordinate';

  @override
  String get tripBuilderTripSaved => 'Trip created and assigned to the driver.';

  @override
  String get transferTitle => 'Move batter between shops';

  @override
  String get transferHint =>
      'Batter a shop will not take can go to another shop on this trip instead of being left over. The driver still hands over only the plan.';

  @override
  String get transferFrom => 'Take from';

  @override
  String get transferTo => 'Give to';

  @override
  String get transferProduct => 'Product';

  @override
  String transferProductOption(String product, String planned, String unit) {
    return '$product (planned $planned $unit)';
  }

  @override
  String transferQuantity(String unit) {
    return 'How much to move ($unit)';
  }

  @override
  String get transferMove => 'Move';

  @override
  String get transferPositive => 'Enter a positive quantity';

  @override
  String get transferNeedsTwoStops =>
      'Add at least two unconfirmed shops before moving batter.';

  @override
  String get shopTitle => 'Supermarkets';

  @override
  String get shopAdd => 'Add supermarket';

  @override
  String get shopEdit => 'Edit supermarket';

  @override
  String get shopName => 'Supermarket name';

  @override
  String get shopAddress => 'Address';

  @override
  String get shopLatitude => 'Latitude';

  @override
  String get shopLongitude => 'Longitude';

  @override
  String get shopUsualOrder => 'Usual allocation';

  @override
  String get shopUsualOrderHint =>
      'Applied automatically when a trip includes this shop. Leave empty if the shop does not take a fixed amount.';

  @override
  String get shopInactive => 'Inactive';

  @override
  String get shopNoOrder => 'No usual allocation yet';

  @override
  String shopOrderSummary(String quantity, String unit, String product) {
    return '$quantity $unit $product';
  }

  @override
  String get shopProductIncomplete =>
      'Each product needs a name, a positive quantity and a unit';

  @override
  String get shopNameRequired => 'Enter the name';

  @override
  String get adminActiveDrivers => 'Active drivers';

  @override
  String adminLiveRides(int count) {
    return '$count live rides';
  }

  @override
  String get adminNoRides => 'No active rides';

  @override
  String get adminNoRidesHint => 'Drivers appear here when they start a ride.';

  @override
  String get stateStart => 'Start';

  @override
  String get stateVia => 'Via';

  @override
  String get stateDestination => 'Destination';

  @override
  String get statePending => 'Pending';

  @override
  String get stateArrived => 'Arrived';

  @override
  String get stateDelivered => 'Delivered';

  @override
  String get statePartial => 'Partial';

  @override
  String get stateFailed => 'Failed';

  @override
  String get deliveriesErpEmpty =>
      'Create a submitted delivery trip with a driver in ERPNext, and a driver account in RouteOS, first.';

  @override
  String get deliveriesAssignErpTitle => 'Assign ERPNext delivery';

  @override
  String get deliveriesMatchingDriver => 'Matching RouteOS driver';

  @override
  String get deliveriesDriverWarning =>
      'Check the driver carefully. This links their accounts; existing delivery confirmations will not be reset.';

  @override
  String get deliveriesExtraNote => 'Planned into a later trip';

  @override
  String get deliveriesAssignProductsTitle => 'Assign products and quantities';

  @override
  String get deliveriesAssignHint =>
      'Examples: Milk in litres, Batter in kg, Curd in packets. Use the same unit when the driver confirms delivery.';

  @override
  String get deliveriesUnitLabel => 'Unit (L, kg, packets, etc.)';

  @override
  String get deliveriesRemoveLast => 'Remove last product';

  @override
  String get deliveriesSyncQueued =>
      'Sync queued. It runs within 30 seconds; refresh to see the result.';

  @override
  String get deliveriesSyncBusy => 'Sync is already running.';

  @override
  String deliveriesSyncCounts(int synced, int failed) {
    return '$synced synced, $failed failed. Failed updates are kept for retry.';
  }

  @override
  String deliveriesLastGps(String latitude, String longitude) {
    return 'Last GPS: $latitude, $longitude';
  }

  @override
  String deliveriesRecordedAt(String time) {
    return 'Recorded: $time';
  }

  @override
  String deliveriesRide(String status) {
    return 'Ride: $status';
  }

  @override
  String get deliveriesLinkHint =>
      'Driver: start a saved route using the ERP vehicle number, then link the ride here.';

  @override
  String deliveriesNote(String note) {
    return 'Delivery Note: $note';
  }

  @override
  String get deliveriesGpsNote =>
      'GPS arrival alone does not confirm delivery. Final outcomes cannot be overwritten.';

  @override
  String tripBuilderCreateFailed(String error) {
    return 'Could not create the trip: $error';
  }

  @override
  String get tripBuilderTripReferenceRequired => 'Enter a trip reference';

  @override
  String get tripBuilderVehicleRequired => 'Enter the vehicle number';

  @override
  String get deliveriesRefresh => 'Refresh deliveries';

  @override
  String get shopRefresh => 'Refresh supermarkets';
}
