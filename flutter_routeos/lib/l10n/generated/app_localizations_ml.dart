// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Malayalam (`ml`).
class AppStringsMl extends AppStrings {
  AppStringsMl([String locale = 'ml']) : super(locale);

  @override
  String get appTitle => 'RouteOS';

  @override
  String get actionSignIn => 'സൈൻ ഇൻ';

  @override
  String get actionSignOut => 'സൈൻ ഔട്ട്';

  @override
  String get actionCancel => 'റദ്ദാക്കുക';

  @override
  String get actionConfirm => 'ഉറപ്പാക്കുക';

  @override
  String get actionSave => 'സംരക്ഷിക്കുക';

  @override
  String get actionRetry => 'വീണ്ടും ശ്രമിക്കുക';

  @override
  String get actionRefresh => 'പുതുക്കുക';

  @override
  String get actionDelete => 'ഇല്ലാതാക്കുക';

  @override
  String get actionAdd => 'ചേർക്കുക';

  @override
  String get actionEdit => 'തിരുത്തുക';

  @override
  String get loginTitle => 'RouteOS-ലേക്ക് സൈൻ ഇൻ ചെയ്യുക';

  @override
  String get loginAccountName => 'അക്കൗണ്ടിന്റെ പേര്';

  @override
  String get loginPassword => 'പാസ്‌വേഡ്';

  @override
  String get loginTagline => 'നിങ്ങളുടെ വഴികൾ. നിങ്ങളുടെ റോഡ്.';

  @override
  String get loginHeadline => 'ഓടുക. രേഖപ്പെടുത്തുക. എത്തിക്കുക.';

  @override
  String get loginSigningIn =>
      'സൈൻ ഇൻ ചെയ്യുന്നു… സെർവർ ഉണർന്നതിന് ഒരു മിനിറ്റ് വേണം.';

  @override
  String get loginSessionExpired =>
      'സെഷൻ കാലാവധി കഴിഞ്ഞു. തുടരാൻ വീണ്ടും സൈൻ ഇൻ ചെയ്യുക.';

  @override
  String get loginNoToken =>
      'സംരക്ഷിച്ച ടോക്കൻ ലഭ്യമല്ല. തുടരാൻ സൈൻ ഇൻ ചെയ്യുക.';

  @override
  String get loginConfigureServer => 'സെർവർ ക്രമീകരിക്കുക';

  @override
  String get loginServerTitle => 'RouteOS സെർവർ URL (ലോക്കൽ അല്ലെങ്കിൽ HTTPS)';

  @override
  String get loginServerTitleHttps => 'RouteOS സെർവർ HTTPS URL';

  @override
  String get loginServerConfigured => 'സെർവർ ക്രമീകരിച്ചു.';

  @override
  String get loginSwitchAccount => 'അക്കൗണ്ട് മാറ്റണോ?';

  @override
  String get tabHome => 'ഹോം';

  @override
  String get tabRoutes => 'വഴികൾ';

  @override
  String get tabDraw => 'വരയ്ക്കുക';

  @override
  String get drawTitle => 'വഴി വരയ്ക്കുക';

  @override
  String drawPoints(int count, String state) {
    return '$count പോയിന്റുകൾ · $state';
  }

  @override
  String get drawUndo => 'പഴയപടിയാക്കുക';

  @override
  String get drawRedo => 'വീണ്ടും ചെയ്യുക';

  @override
  String get drawClear => 'വഴി മായ്ക്കുക';

  @override
  String get drawPointsList => 'വഴിയുടെ പോയിന്റുകൾ';

  @override
  String get drawUseMyLocation => 'എന്റെ സ്ഥാനം ഒരു പോയിന്റായി ഉപയോഗിക്കുക';

  @override
  String get drawSave => 'വഴി സംരക്ഷിക്കുക';

  @override
  String get drawStart => 'നാവിഗേഷൻ തുടങ്ങുക';

  @override
  String get drawOptimize => 'വേപ്പോയിന്റുകളുടെ ക്രമം ഒപ്റിമൈസ് ചെയ്യുക';

  @override
  String get drawRecord => 'വഴി റെക്കോർഡ് ചെയ്യുക';

  @override
  String get drawEditRoute => 'വഴി വരയ്ക്കുക';

  @override
  String get drawMaxPoints =>
      'തുടക്കവും ലക്ഷ്യവും ഉൾപ്പെടുത്തി പരമാവധി 100 വേപ്പോയിന്റുകൾ.';

  @override
  String get pointStart => 'തുടക്കം';

  @override
  String get pointVia => 'വഴിയായി';

  @override
  String get pointDestination => 'ലക്ഷ്യസ്ഥാനം';

  @override
  String get searchTitle => 'ലക്ഷ്യസ്ഥാനം തിരയുക';

  @override
  String get searchHint =>
      'ഓഫ്‌ലൈൻ സ്ഥലങ്ങളും വിലാസങ്ങളും തിരയുക. മൾദേശീയ ഭൂപടം ഇറക്കിയാൽ ഫലങ്ങൾ ലഭിക്കും.';

  @override
  String get searchClear => 'തിരയേറ്റുസൂക്കുക';

  @override
  String get deliveriesTitle => 'ഡെലിവറികൾ';

  @override
  String get deliveriesCreateTrip => 'ട്രിപ്പ് സൃഷ്ടിക്കുക';

  @override
  String get deliveriesAssignErp => 'ERPNext ട്രിപ്പ് നിയോമിതമാക്കുക';

  @override
  String get deliveriesSyncErp => 'ERPNext-ലേക്ക് സമന്യസ് ചെയ്യുക';

  @override
  String get deliveriesSupermarkets => 'സൂപ്പർമാർക്കറ്റുകൾ';

  @override
  String get deliveriesEmpty => 'ഡെലിവറി അസൈൻമെന്റുകളില്ല';

  @override
  String get deliveriesEmptyHint =>
      'ഒരു അഡ്മിൻ ഇവിടെ ട്രിപ്പ് സൃഷ്ടിക്കാം, അല്ലെങ്കിൽ ERPNext ട്രിപ്പ് ഇറക്കും. ഡ്രൈവർമാർക്ക് സ്വന്തം അസൈൻമെന്റുകൾ മാത്രം കാണാം.';

  @override
  String get deliveriesLinkRide => 'എന്റെ നിലവിലെ റൈഡ് ബന്ധിപ്പിക്കുക';

  @override
  String get deliveriesMoveBatter => 'കടയുടെ മാറ്റുക';

  @override
  String deliveriesStillToHandOver(String items) {
    return 'ഇപ്പോഴും നൽലേണ്ടത്: $items';
  }

  @override
  String get deliveriesAssignProducts => 'ഉൽപ്പന്നങ്ങൾ നിയോമിതമാക്കുക';

  @override
  String get deliveriesExtraTitle => 'കടകൾ ആവശ്യപ്പെട്ട അധികം';

  @override
  String get deliveriesExtraHint =>
      'ഡ്രൈവർമാർ പ്ലാന് പ്രകാരം മാത്രമാണ് നൽകിയത്. ഇത് പിന്നീട് ട്രിപ്പിലേക്ക് ഉൾപ്പെടുത്തുക, അല്ലെങ്കിൽ മറ്റൊരു കടയ്ക്ക് നൽകുക.';

  @override
  String get deliveriesExtraRecorded => 'ഒരിക്കൽ രേഖപ്പെടുത്തി';

  @override
  String deliveriesExtraRecordedMany(int count) {
    return '$count തവണ രേഖപ്പെടുത്തി';
  }

  @override
  String get deliveriesExtraPlanned => 'പ്ലാൻ ചെയ്തു';

  @override
  String deliveriesExtraResolved(
    String shop,
    String amount,
    String unit,
    String product,
  ) {
    return '$shop $amount $unit $product കാത്തിരിക്കുന്നില്ല.';
  }

  @override
  String get confirmTitleDelivered => 'വിശേരിച്ചുവന്നതാണോ?';

  @override
  String get confirmTitlePartial => 'കുറവുള്ള ഡെലിവറി രേഖപ്പെടുത്താണോ?';

  @override
  String get confirmTitleFailed => 'വിപത്ത് രേഖപ്പെടുത്താണോ?';

  @override
  String get confirmTitleArrived => 'എത്തിച്ചത് രേഖപ്പെടുത്താണോ?';

  @override
  String get confirmGpsNote =>
      'GPS എത്തിച്ചത് കൊണ്ട് മാത്രം ഡെലിവറി ഉറപ്പാകുന്നില്ല. അന്തിമ ഫലങ്ങൾ മാറ്റാനാവില്ല.';

  @override
  String get confirmNoProducts =>
      'ഉൽപ്പന്നങ്ങൾ നിയോമിതമാക്കിയില്ല. അഡ്മിനിനേ ആദ്യം ചേർക്കാൻ പറയുക.';

  @override
  String confirmDeliveredLabel(String product, String unit) {
    return '$product നൽകിയത് ($unit)';
  }

  @override
  String confirmAssigned(String quantity, String unit) {
    return 'നിയോമിതം: $quantity $unit';
  }

  @override
  String get confirmExtraLabel => 'ഈ കട അടുത്ത ട്രിപ്പിന് ആവശ്യപ്പെട്ട അധികം';

  @override
  String get confirmExtraHint =>
      'രേഖപ്പെടുത്തുക മാത്രം. ഇപ്പോൾ അധികം ഒന്നും നൽകില്ല.';

  @override
  String get confirmExtraPositive => '3 ദശാംശം വരെ പോസിറ്റീവ് ആണ് അടയ്ക്കുക';

  @override
  String get confirmPartialReason => 'കുറവിന്റെ കാരണം';

  @override
  String get confirmFailedReason => 'ഡെലിവറി പരാജയപ്പെട്ടതേക്കാണ്?';

  @override
  String get confirmReasonRequired => 'കാരണം നൽകണം';

  @override
  String get confirmUsePartial =>
      'കുറവുണ്ടെങ്കിൽ റദ്ദാക്കി partial ഡെലിവറി തിരഞ്ഞെടുക്കുക';

  @override
  String confirmQuantityRange(String planned) {
    return '0 മുതൽ $planned വരെ, 3 ദശാംശം വരെ ടൈപ്പ് ചെയ്യുക';
  }

  @override
  String confirmDeliveredSummary(
    String product,
    String delivered,
    String planned,
    String unit,
  ) {
    return '$product: $planned $unit ലെ നൽകിയത് $delivered';
  }

  @override
  String get tripBuilderTitle => 'ട്രിപ്പ് സൃഷ്ടിക്കുക';

  @override
  String get tripBuilderReference => 'ട്രിപ്പ് റെഫറൻസ്';

  @override
  String get tripBuilderReferenceHint =>
      'ഉദാഹരണത്തിന് SAP-TRIP-1042. അത് വീണ്ടും ഉപയോഗിച്ചാൽ ട്രിപ്പ് പകർപ്പാകില്ല.';

  @override
  String get tripBuilderDriver => 'ഡ്രൈവർ';

  @override
  String get tripBuilderVehicle => 'വാഹന നമ്പർ';

  @override
  String get tripBuilderVehicleHint =>
      'ഡ്രൈവർ ഈ വാഹനം ഉപയോഗിച്ച് റൈഡ് തുടങ്ങണം.';

  @override
  String get tripBuilderSupermarkets => 'സൂപ്പർമാർക്കറ്റുകൾ';

  @override
  String get tripBuilderAddSupermarket => 'സൂപ്പർമാർക്കറ്റ് ചേർക്കുക';

  @override
  String tripBuilderStopTitle(int number) {
    return 'സൂപ്പർമാർക്കറ്റ് $number';
  }

  @override
  String get tripBuilderShopName => 'സൂപ്പർമാർക്കറ്റിന്റെ പേര്';

  @override
  String get tripBuilderAddress => 'വിലാസം';

  @override
  String get tripBuilderLatitude => 'അക്ഷാംശം';

  @override
  String get tripBuilderLongitude => 'ദോംശം';

  @override
  String get tripBuilderProducts => 'നൽകേണ്ട ഉൽപ്പന്നങ്ങൾ';

  @override
  String get tripBuilderAddProduct => 'ഉൽപ്പന്നം ചേർക്കുക';

  @override
  String get tripBuilderRemoveProduct => 'ഉൽപ്പന്നം നീക്കുക';

  @override
  String get tripBuilderProduct => 'ഉൽപ്പന്നം';

  @override
  String get tripBuilderQuantity => 'അളവ്';

  @override
  String get tripBuilderUnit => 'യൂണിറ്റ്';

  @override
  String get tripBuilderSaveStop => 'സ്റ്റോപ്പ് സംരക്ഷിക്കുക';

  @override
  String get tripBuilderStopNeedsProduct =>
      'ഡ്രൈവർ ഡെലിവറി ഉറപ്പാക്കാൻ കുറഞ്ഞത് ഒരു ഉൽപ്പന്നം ചേർക്കുക';

  @override
  String get tripBuilderProductIncomplete =>
      'ഓരോ ഉൽപ്പന്നത്തിനും പേര്, പോസിറ്റീവ് അളവ്, യൂണിറ്റ് എന്നിവ വേണം';

  @override
  String get tripBuilderStopWithoutProducts =>
      'ഓരോ സൂപ്പർമാർക്കറ്റിനും കുറഞ്ഞത് ഒരു ഉൽപ്പന്നവും അളവും വേണം, അല്ലെങ്കിൽ ഡ്രൈവർക്ക് ഡെലിവറി ഉറപ്പാക്കാനാവില്ല.';

  @override
  String get tripBuilderCreate => 'ട്രിപ്പ് സൃഷ്ടിക്കുക';

  @override
  String get tripBuilderCreated => 'ട്രിപ്പ് സൃഷ്ടിച്ച് ഡ്രൈവർക്ക് നൽകി.';

  @override
  String get tripBuilderCoordinateRange => 'പരിധിയ്ക്ക് പുറത്ത്';

  @override
  String get tripBuilderCoordinateMissing => 'ഒരു നിരയോടി നൽകുക';

  @override
  String get tripBuilderTripSaved => 'ട്രിപ്പ് സൃഷ്ടിച്ച് ഡ്രൈവർക്ക് നൽകി.';

  @override
  String get transferTitle => 'കടകൾക്കിടയിൽ ബാറ്റർ മാറ്റുക';

  @override
  String get transferHint =>
      'കടം സ്വീകരിക്കാത്ത ബാറ്റർ ഈ ട്രിപ്പിലെ മറ്റൊരു കടയ്ക്ക് നൽകാം. ഡ്രൈവർ പ്ലാൻ പ്രകാരം മാത്രമാണ് നൽകുന്നത്.';

  @override
  String get transferFrom => 'എടുക്കുക';

  @override
  String get transferTo => 'നൽകുക';

  @override
  String get transferProduct => 'ഉൽപ്പന്നം';

  @override
  String transferProductOption(String product, String planned, String unit) {
    return '$product (പ്ലാൻ $planned $unit)';
  }

  @override
  String transferQuantity(String unit) {
    return 'എത്ര മാറ്റണം ($unit)';
  }

  @override
  String get transferMove => 'മാറ്റുക';

  @override
  String get transferPositive => 'പോസിറ്റീവ് ആണ് അളവ് നൽകുക';

  @override
  String get transferNeedsTwoStops =>
      'ബാറ്റർ മാറ്റാൻ കുറഞ്ഞത് രണ്ട് കടകൾ ചേർക്കുക.';

  @override
  String get shopTitle => 'സൂപ്പർമാർക്കറ്റുകൾ';

  @override
  String get shopAdd => 'സൂപ്പർമാർക്കറ്റ് ചേർക്കുക';

  @override
  String get shopEdit => 'സൂപ്പർമാർക്കറ്റ് തിരുത്തുക';

  @override
  String get shopName => 'സൂപ്പർമാർക്കറ്റിന്റെ പേര്';

  @override
  String get shopAddress => 'വിലാസം';

  @override
  String get shopLatitude => 'അക്ഷാംശം';

  @override
  String get shopLongitude => 'ദോംശം';

  @override
  String get shopUsualOrder => 'സാധാരണ അളവ്';

  @override
  String get shopUsualOrderHint =>
      'ട്രിപ്പിലുള്ള ഈ കടയ്ക്ക് ഓട്ടോമാറ്റിക്കായി പ്രയോഗിക്കുന്നു. സ്ഥിരമായ അളവില്ലാത്ത കടകൾക്ക് ശൂന്യമാക്കാം.';

  @override
  String get shopInactive => 'നിർത്തിവച്ചത്';

  @override
  String get shopNoOrder => 'സാധാരണ അളവ് ഇല്ല';

  @override
  String shopOrderSummary(String quantity, String unit, String product) {
    return '$quantity $unit $product';
  }

  @override
  String get shopProductIncomplete =>
      'ഓരോ ഉൽപ്പന്നത്തിനും പേര്, പോസിറ്റീവ് അളവ്, യൂണിറ്റ് എന്നിവ വേണം';

  @override
  String get shopNameRequired => 'പേര് നൽകുക';

  @override
  String get adminActiveDrivers => 'സജീവ ഡ്രൈവർമാർ';

  @override
  String adminLiveRides(int count) {
    return '$count സജീവ റൈഡുകൾ';
  }

  @override
  String get adminNoRides => 'സജീവ റൈഡുകളില്ല';

  @override
  String get adminNoRidesHint => 'ഡ്രൈവർമാർ റൈഡ് തുടങ്ങിയാൽ ഇവിടെ കാണാം.';

  @override
  String get stateStart => 'തുടക്കം';

  @override
  String get stateVia => 'വഴിയായി';

  @override
  String get stateDestination => 'ലക്ഷ്യസ്ഥാനം';

  @override
  String get statePending => 'തീർമ്മായിട്ടില്ല';

  @override
  String get stateArrived => 'എത്തി';

  @override
  String get stateDelivered => 'നൽകി';

  @override
  String get statePartial => 'കുറവ്';

  @override
  String get stateFailed => 'പരാജയം';

  @override
  String get deliveriesErpEmpty =>
      'ആദ്യം ERPNext-ൽ ഡ്രൈവറുമുള്ള സമർജിച്ച ഡെലിവറി ട്രിപ്പും RouteOS-ൽ ഒരു ഡ്രൈവർ അക്കൗണ്ടും ഉണ്ടാക്കുക.';

  @override
  String get deliveriesAssignErpTitle => 'ERPNext ഡെലിവറി നിയോമിതമാക്കുക';

  @override
  String get deliveriesMatchingDriver => 'പൊരുത്തമായ RouteOS ഡ്രൈവർ';

  @override
  String get deliveriesDriverWarning =>
      'ഡ്രൈവറെ ശ്രദ്ധയോടെ പരിശോധിക്കുക. ഇത് അവരുടെ അക്കൗണ്ടുകൾ ബന്ധിപ്പിക്കും; നിലവിലെ ഡെലിവറി രേഖകൾ റിസെറ്റ് ആകില്ല.';

  @override
  String get deliveriesExtraNote => 'പിന്നീടുള്ള ട്രിപ്പിൽ ഉൾപ്പെടുത്തി';

  @override
  String get deliveriesAssignProductsTitle =>
      'ഉൽപ്പന്നങ്ങളും അളവുകളും നിയോമിതമാക്കുക';

  @override
  String get deliveriesAssignHint =>
      'ഉദാഹരണങ്ങൾ: മില്ക് ലിറ്ററിൽ, ബാറ്റർ കിലോയിൽ, കുർട്ട് പാക്കറ്റിൽ. ഡ്രൈവർ ഡെലിവറി ഉറപ്പാക്കുമ്പോൾ അതേ യൂണിറ്റ് ഉപയോഗിക്കുക.';

  @override
  String get deliveriesUnitLabel => 'യൂണിറ്റ് (L, kg, പാക്കറ്റുകൾ എന്നിവ)';

  @override
  String get deliveriesRemoveLast => 'അവസാന ഉൽപ്പന്നം നീക്കുക';

  @override
  String get deliveriesSyncQueued =>
      'സമന്യസ് അനുവയിച്ചു. 30 സെക്കൻഡിനുള്ളിൽ ഓടും; ഫലം കാണാൻ പുതുക്കുക.';

  @override
  String get deliveriesSyncBusy => 'സമന്യസ് ഇപ്പോഴും നടക്കുന്നു.';

  @override
  String deliveriesSyncCounts(int synced, int failed) {
    return '$synced സമന്യസ് ആയി, $failed പരാജയപ്പെട്ടു. പരാജയപ്പെട്ടവ വീണ്ടും ശ്രമിക്കുന്നതിന് സംരക്ഷിക്കുന്നു.';
  }

  @override
  String deliveriesLastGps(String latitude, String longitude) {
    return 'അവസാന GPS: $latitude, $longitude';
  }

  @override
  String deliveriesRecordedAt(String time) {
    return 'രേഖപ്പെടുത്തിയത്: $time';
  }

  @override
  String deliveriesRide(String status) {
    return 'റൈഡ്: $status';
  }

  @override
  String get deliveriesLinkHint =>
      'ഡ്രൈവർ: ERP വാഹന നമ്പറുമായി സംരക്ഷിച്ച വഴി തുടങ്ങി, അതിനു ശേഷം റൈഡ് ബന്ധിപ്പിക്കുക.';

  @override
  String deliveriesNote(String note) {
    return 'ഡെലിവറി നോട്ട്: $note';
  }

  @override
  String get deliveriesGpsNote =>
      'GPS എത്തിച്ചത് കൊണ്ട് മാത്രം ഡെലിവറി ഉറപ്പാകുന്നില്ല. അന്തിമ ഫലങ്ങൾ മാറ്റാനാവില്ല.';

  @override
  String tripBuilderCreateFailed(String error) {
    return 'ട്രിപ്പ് സൃഷ്ടിക്കാൻ കഴിഞ്ഞില്ല: $error';
  }

  @override
  String get tripBuilderTripReferenceRequired => 'ട്രിപ്പ് റെഫറൻസ് നൽകുക';

  @override
  String get tripBuilderVehicleRequired => 'വാഹന നമ്പർ നൽകുക';

  @override
  String get deliveriesRefresh => 'ഡെലിവറികൾ പുതുക്കുക';

  @override
  String get shopRefresh => 'സൂപ്പർമാർക്കറ്റുകൾ പുതുക്കുക';

  @override
  String get tabAccount => 'അക്കൗണ്ട്';

  @override
  String get routesFilterAll => 'എല്ലാവും';

  @override
  String get routesTitle => 'എന്റെ വഴികൾ';

  @override
  String get routesSavedTitle => 'സംരക്ഷിച്ച വഴികൾ';

  @override
  String get routesEmpty =>
      'ഇതുവരെ സംരക്ഷിച്ച വഴികളില്ല. നിങ്ങളുടെ ആദ്യ വഴി ഒരുക്കുക അല്ലെങ്കിൽ റെക്കോർഡ് ചെയ്യുക.';

  @override
  String get routesSearch => 'സംരക്ഷിച്ച വഴികൾ തിരയുക';

  @override
  String get routesFavourites => 'ഇഷ്ടപ്പെട്ടവ';

  @override
  String get routesRemoveRecent => 'അടുത്ത വഴികളിൽ നിന്ന് നീക്കുക';

  @override
  String get routeCalculateFailed =>
      'ഈ വഴി കണക്കാക്കാൻ കഴിഞ്ഞില്ല. ഓഫ്‌ലൈൻ ഭൂപടം പരിശോധിച്ച് വീണ്ടും ശ്രമിക്കുക.';

  @override
  String get routeLoadFailed =>
      'ഈ വഴി ലോഡ് ചെയ്യാൻ കഴിഞ്ഞില്ല. കണക്ഷൻ പരിശോധിച്ച് വീണ്ടും ശ്രമിക്കുക.';

  @override
  String get routeTimeout =>
      'വഴി കണക്കാക്കുന്നതിന് സമയം കഴിഞ്ഞു. മൾദേശീയ ഭൂപടങ്ങൾ പരിശോധിച്ച് വീണ്ടും ശ്രമിക്കുക.';

  @override
  String get routeName => 'വഴിയുടെ പേര്';

  @override
  String get routeDelete => 'വഴി ഇല്ലാതാക്കുക';

  @override
  String get routeRename => 'വഴിയുടെ പേര് മാറ്റുക';

  @override
  String get routeShare => 'വഴി പങ്കിടുക';

  @override
  String get routeOpen => 'വരച്ച വഴി തുറക്കുക / തിരുത്തുക';

  @override
  String get routeFollow => 'വഴി പിന്തുടരുക';

  @override
  String get routeFavouriteToggle => 'ഇഷ്ടപ്പെട്ടതായി മാറ്റുക';

  @override
  String get routeSaved => 'വഴി സംരക്ഷിതമായി. മറ്റ് ഡ്രൈവർമാർക്കും ലഭ്യമാണ്.';

  @override
  String get routeShared => 'വഴി RouteOS ഡ്രൈവർമാരുമായി പങ്കിടുത്തു.';

  @override
  String get drawOptimizeTitle => 'വേപ്പോയിന്റുകളുടെ ക്രമം ഒപ്റിമൈസ് ചെയ്യണോ?';

  @override
  String get drawOrganicsLimit =>
      'Organic Maps-ലേക്ക് തുടക്കവും ലക്ഷ്യവും ഉൾപ്പെടുത്തി 100 വേപ്പോയിന്റുകൾ മാത്രമാണ് പോകാവുന്നത്.';

  @override
  String get drawDriverOnly =>
      'വഴി വരയ്ക്കുക ഡ്രൈവർമാർക്ക് മാത്രമാണ് ലഭ്യമാകുക.';

  @override
  String get drawMaxPointsReached => 'പരമാവധി 102 വഴിപോയിന്റുകൾ എത്തി.';

  @override
  String get pointDelete => 'പോയിന്റ് ഇല്ലാതാക്കുക';

  @override
  String get pointInsertAfter => 'ശേഷം ചേർക്കുക';

  @override
  String get pointMoveOnMap => 'മാപ്പിൽ നീക്കുക';

  @override
  String get pointMoveEarlier => 'മുമ്പിലേക്ക് നീക്കുക';

  @override
  String get pointMoveLater => 'പിന്നിലേക്ക് നീക്കുക';

  @override
  String get pointMoveTap => 'ഈ പോയിന്റിനായി പുതിയ സ്ഥാനത്തിൽ ടാപ്പ് ചെയ്യുക';

  @override
  String get pointInsertTap => 'ഒരു പോയിന്റ് ചേർക്കാൻ ടാപ്പ് ചെയ്യുക';

  @override
  String get pointEdit => 'പോയിന്റ് തിരുത്തുക';

  @override
  String pointLabel(int number, String type) {
    return 'പോയിന്റ് $number · $type';
  }

  @override
  String get mapMyLocation => 'എന്റെ സ്ഥാനം';

  @override
  String get mapZoomIn => 'സമീപിക്കുക';

  @override
  String get mapZoomOut => 'അകനാക്കുക';

  @override
  String get mapDownloads => 'ഓഫ്‌ലൈൻ ഭൂപടങ്ങൾ';

  @override
  String get searchPlaces => 'സ്ഥലങ്ങൾ തിരയുക';

  @override
  String get vehicleSelect => 'വാഹനം തിരഞ്ഞെടുക്കുക';

  @override
  String get rideStart => 'റൈഡ് തുടങ്ങുക';

  @override
  String get rideEnd => 'റൈഡ് അവസാനിപ്പിക്കുക';

  @override
  String get rideEndTitle => 'ഈ റൈഡ് അവസാനിപ്പിക്കണോ?';

  @override
  String get rideWaitingGps => 'റൈഡ് സജീവം — GPS കാത്തിരിക്കുന്നു';

  @override
  String get rideWaitingGuidance => 'GPS മാർഗനിർദേശം കാത്തിരിക്കുന്നു';

  @override
  String get rideStarting => 'നാവിഗേഷൻ തുടങ്ങുന്നു — കാത്തിരിക്കുക.';

  @override
  String get rideLiveTrackingNote =>
      'RouteOS റൈഡ് അവസാനിച്ചതാണെന്ന് സ്ഥിരീകരിച്ച ശേഷം ലൈവ് ട്രാക്കിംഗ് നിർത്തും.';

  @override
  String get rideLoadPrompt =>
      'വഴി ലോഡ് ചെയ്ത് വാഹനം തിരഞ്ഞെടുത്ത് നാവിഗേഷൻ തുടങ്ങുക';

  @override
  String get rideLocationMissing => 'ലഭിച്ചില്ല';

  @override
  String get rideEndNavigationFirst =>
      'വഴി തിരുത്തുന്നതിന് മുമ്പ് നാവിഗേഷൻ അവസാനിപ്പിക്കുക.';

  @override
  String get recordStopSave => 'നിർത്തി സംരക്ഷിക്കുക';

  @override
  String get recordDiscard => 'ഉപേക്ഷിക്കുക';

  @override
  String get recordDiscardTitle => 'റെക്കോർഡിംഗ് ഉപേക്ഷിക്കണോ?';

  @override
  String get recordStopFirst =>
      'ആദ്യം റെക്കോർഡിംഗ് നിർത്തുക അല്ലെങ്കിൽ ഉപേക്ഷിക്കുക.';

  @override
  String get recordDiscardHint =>
      'നേറ്റീവ് റെക്കോർഡർ നിർത്തി സംരക്ഷിക്കാത്ത ട്രാക്ക് ഉപേക്ഷിക്കുക.';

  @override
  String get recordSeparateNote =>
      'അസൽ ജിപിഎസ് ട്രാക്ക് വരച്ച വഴികളിൽ നിന്ന് വേർതിരിച്ച് സൂക്ഷിക്കുന്നു.';

  @override
  String recordProgress(String distance) {
    return 'റെക്കോർഡിംഗ് വഴി · $distance';
  }

  @override
  String sessionRestoreFailed(String error) {
    return 'നിങ്ങളുടെ സെഷൻ പുനഃസ്ഥാപിക്കാനായില്ല: $error';
  }

  @override
  String get screenClosed => 'സ്ക്രീൻ അടച്ചു';

  @override
  String get loginDevelopmentAccounts => 'ഡെവലപ്മെന്റ് അക്കൗണ്ടുകൾ';

  @override
  String get actionRename => 'പേര് മാറ്റുക';

  @override
  String get adminRefreshRides => 'സജീവ റൈഡുകൾ പുതുക്കുക';

  @override
  String get reportsTitle => 'ഡെലിവറി റിപ്പോർട്ടുകൾ';

  @override
  String get reportsShortages => 'കുറവുകളും പരാജയങ്ങളും';

  @override
  String get reportsTotals => 'ഉൽപ്പന്നം അനുസരിച്ചുള്ള ആകെകൾ';

  @override
  String get reportsTrips => 'ട്രിപ്പുകൾ';

  @override
  String get reportsEmpty => 'ഇതുവരെ ഡെലിവറികൾ രേഖപ്പെടുത്തിയിട്ടില്ല.';
}
