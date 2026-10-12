// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Arabic (`ar`).
class AppStringsAr extends AppStrings {
  AppStringsAr([String locale = 'ar']) : super(locale);

  @override
  String get appTitle => 'RouteOS';

  @override
  String get actionSignIn => 'تسجيل الدخول';

  @override
  String get actionSignOut => 'تسجيل الخروج';

  @override
  String get actionCancel => 'إلغاء';

  @override
  String get actionConfirm => 'تأكيد';

  @override
  String get actionSave => 'حفظ';

  @override
  String get actionRetry => 'إعادة المحاولة';

  @override
  String get actionRefresh => 'تحديث';

  @override
  String get actionDelete => 'حذف';

  @override
  String get actionAdd => 'إضافة';

  @override
  String get actionEdit => 'تعديل';

  @override
  String get loginTitle => 'تسجيل الدخول إلى RouteOS';

  @override
  String get loginAccountName => 'اسم الحساب';

  @override
  String get loginPassword => 'كلمة المرور';

  @override
  String get loginTagline => 'مساراتك. طريقك.';

  @override
  String get loginHeadline => 'قُد. سجّل. سلّم.';

  @override
  String get loginSigningIn =>
      'جارٍ تسجيل الدخول… قد يستغرق الخادم دقيقة للاستيقاظ.';

  @override
  String get loginSessionExpired =>
      'انتهت صلاحية الجلسة. سجّل الدخول مرة أخرى للمتابعة.';

  @override
  String get loginNoToken => 'لا يوجد رمز محفوظ. سجّل الدخول للمتابعة.';

  @override
  String get loginConfigureServer => 'ضبط الخادم';

  @override
  String get loginServerTitle => 'عنوان خادم RouteOS (محلي أو HTTPS)';

  @override
  String get loginServerTitleHttps => 'عنوان خادم RouteOS عبر HTTPS';

  @override
  String get loginServerConfigured => 'تم ضبط الخادم.';

  @override
  String get loginSwitchAccount => 'تبديل الحساب؟';

  @override
  String get tabHome => 'الرئيسية';

  @override
  String get tabRoutes => 'المسارات';

  @override
  String get tabDraw => 'رسم';

  @override
  String get drawTitle => 'رسم مسار';

  @override
  String drawPoints(int count, String state) {
    return '$count نقطة · $state';
  }

  @override
  String get drawUndo => 'تراجع';

  @override
  String get drawRedo => 'إعادة';

  @override
  String get drawClear => 'مسح المسار';

  @override
  String get drawPointsList => 'نقاط المسار';

  @override
  String get drawUseMyLocation => 'استخدم موقعي كنقطة';

  @override
  String get drawSave => 'حفظ المسار';

  @override
  String get drawStart => 'بدء الملاحة';

  @override
  String get drawOptimize => 'ترتيب نقاط التوقف';

  @override
  String get drawRecord => 'تسجيل المسار';

  @override
  String get drawEditRoute => 'رسم مسار';

  @override
  String get drawMaxPoints => 'الحد الأقصى 100 نقطة إضافة إلى البداية والوجهة.';

  @override
  String get pointStart => 'البداية';

  @override
  String get pointVia => 'عبر';

  @override
  String get pointDestination => 'الوجهة';

  @override
  String get searchTitle => 'ابحث عن الوجهة';

  @override
  String get searchHint =>
      'ابحث في الأماكن والعناوين دون اتصال. نزّل خريطة المنطقة للحصول على نتائج محلية.';

  @override
  String get searchClear => 'مسح البحث';

  @override
  String get deliveriesTitle => 'التوصيلات';

  @override
  String get deliveriesCreateTrip => 'إنشاء رحلة';

  @override
  String get deliveriesAssignErp => 'إسناد رحلة ERPNext';

  @override
  String get deliveriesSyncErp => 'مزامنة مع ERPNext';

  @override
  String get deliveriesSupermarkets => 'أسواق السوبرماركت';

  @override
  String get deliveriesEmpty => 'لا توجد مهام توصيل';

  @override
  String get deliveriesEmptyHint =>
      'يمكن للمشرف إنشاء رحلة هنا أو استيراد رحلة من ERPNext. يرى السائقون مهامهم فقط.';

  @override
  String get deliveriesLinkRide => 'ربط رحلتي الحالية';

  @override
  String get deliveriesMoveBatter => 'نقل بين المحلات';

  @override
  String deliveriesStillToHandOver(String items) {
    return 'لم يُسلَّم بعد: $items';
  }

  @override
  String get deliveriesAssignProducts => 'إسناد المنتجات';

  @override
  String get deliveriesExtraTitle => 'إضافات طلبتها المحلات';

  @override
  String get deliveriesExtraHint =>
      'سلّم السائقون الكمية المخططة فقط. أدرجها في رحلة لاحقة أو أعطها لمحل آخر حتى لا يتبقى شيء.';

  @override
  String get deliveriesExtraRecorded => 'سُجلت مرة واحدة';

  @override
  String deliveriesExtraRecordedMany(int count) {
    return 'سُجلت $count مرات';
  }

  @override
  String get deliveriesExtraPlanned => 'تمت خطتها';

  @override
  String deliveriesExtraResolved(
    String shop,
    String amount,
    String unit,
    String product,
  ) {
    return 'لم يعد $shop بانتظار $amount $unit $product.';
  }

  @override
  String get confirmTitleDelivered => 'تأكيد التسليم؟';

  @override
  String get confirmTitlePartial => 'تسجيل توصيل جزئي؟';

  @override
  String get confirmTitleFailed => 'تسجيل فشل التوصيل؟';

  @override
  String get confirmTitleArrived => 'تسجيل الوصول؟';

  @override
  String get confirmGpsNote =>
      'الوصول عبر GPS وحده لا يؤكد التوصيل. لا يمكن تعديل النتائج النهائية.';

  @override
  String get confirmNoProducts =>
      'لم تُسند منتجات. اطلب من المشرف إضافة المنتجات والكميات أولاً.';

  @override
  String confirmDeliveredLabel(String product, String unit) {
    return 'المسلَّم من $product ($unit)';
  }

  @override
  String confirmAssigned(String quantity, String unit) {
    return 'المسند: $quantity $unit';
  }

  @override
  String get confirmExtraLabel => 'إضافية طلبها هذا المحل في الرحلة القادمة';

  @override
  String get confirmExtraHint => 'تُسجَّل فقط. لا يُسلَّم أي شيء إضافي الآن.';

  @override
  String get confirmExtraPositive => 'أدخل كمية موجبة حتى 3 منازل عشرية';

  @override
  String get confirmPartialReason => 'سبب النقص';

  @override
  String get confirmFailedReason => 'لماذا فشل التوصيل؟';

  @override
  String get confirmReasonRequired => 'السبب مطلوب';

  @override
  String get confirmUsePartial => 'عند النقص، ألغِ واختر توصيلًا جزئيًا';

  @override
  String confirmQuantityRange(String planned) {
    return 'أدخل من 0 إلى $planned، حتى 3 منازل عشرية';
  }

  @override
  String confirmDeliveredSummary(
    String product,
    String delivered,
    String planned,
    String unit,
  ) {
    return '$product: تم تسليم $delivered من $planned $unit';
  }

  @override
  String get tripBuilderTitle => 'إنشاء رحلة';

  @override
  String get tripBuilderReference => 'مرجع الرحلة';

  @override
  String get tripBuilderReferenceHint =>
      'مثال SAP-TRIP-1042. إعادة استخدامه لا تُنشئ رحلة مكررة.';

  @override
  String get tripBuilderDriver => 'السائق';

  @override
  String get tripBuilderVehicle => 'رقم المركبة';

  @override
  String get tripBuilderVehicleHint =>
      'يجب أن يبدأ السائق رحلته بهذه المركبة بالضبط.';

  @override
  String get tripBuilderSupermarkets => 'أسواق السوبرماركت';

  @override
  String get tripBuilderAddSupermarket => 'إضافة سوبرماركت';

  @override
  String tripBuilderStopTitle(int number) {
    return 'سوبرماركت $number';
  }

  @override
  String get tripBuilderShopName => 'اسم السوبرماركت';

  @override
  String get tripBuilderAddress => 'العنوان';

  @override
  String get tripBuilderLatitude => 'خط العرض';

  @override
  String get tripBuilderLongitude => 'خط الطول';

  @override
  String get tripBuilderProducts => 'المنتجات المراد تسليمها';

  @override
  String get tripBuilderAddProduct => 'إضافة منتج';

  @override
  String get tripBuilderRemoveProduct => 'إزالة المنتج';

  @override
  String get tripBuilderProduct => 'المنتج';

  @override
  String get tripBuilderQuantity => 'الكمية';

  @override
  String get tripBuilderUnit => 'الوحدة';

  @override
  String get tripBuilderSaveStop => 'حفظ المحطة';

  @override
  String get tripBuilderStopNeedsProduct =>
      'أضف منتجاً واحداً على الأقل ليتمكن السائق من تأكيد التوصيل';

  @override
  String get tripBuilderProductIncomplete =>
      'كل منتج يحتاج اسماً وكمية موجبة ووحدة';

  @override
  String get tripBuilderStopWithoutProducts =>
      'كل سوبرماركت يحتاج منتجاً واحداً على الأقل وكمية، وإلا لم يتمكن السائق من تأكيد التوصيل.';

  @override
  String get tripBuilderCreate => 'إنشاء الرحلة';

  @override
  String get tripBuilderCreated => 'تم إنشاء الرحلة وإسنادها إلى السائق.';

  @override
  String get tripBuilderCoordinateRange => 'خارج النطاق';

  @override
  String get tripBuilderCoordinateMissing => 'أدخل إحداثياً';

  @override
  String get tripBuilderTripSaved => 'تم إنشاء الرحلة وإسنادها إلى السائق.';

  @override
  String get transferTitle => 'نقل العجين بين المحلات';

  @override
  String get transferHint =>
      'يمكن تسليم العجين الذي لا يوافق عليه محل إلى محل آخر في نفس الرحلة بدلاً من هدره. يسلّم السائق الكمية المخططة فقط.';

  @override
  String get transferFrom => 'نقل من';

  @override
  String get transferTo => 'نقل إلى';

  @override
  String get transferProduct => 'المنتج';

  @override
  String transferProductOption(String product, String planned, String unit) {
    return '$product (مخطط $planned $unit)';
  }

  @override
  String transferQuantity(String unit) {
    return 'كمية النقل ($unit)';
  }

  @override
  String get transferMove => 'نقل';

  @override
  String get transferPositive => 'أدخل كمية موجبة';

  @override
  String get transferNeedsTwoStops =>
      'أضف محطتين غير مؤكدتين على الأقل قبل نقل العجين.';

  @override
  String get shopTitle => 'أسواق السوبرماركت';

  @override
  String get shopAdd => 'إضافة سوبرماركت';

  @override
  String get shopEdit => 'تعديل السوبرماركت';

  @override
  String get shopName => 'اسم السوبرماركت';

  @override
  String get shopAddress => 'العنوان';

  @override
  String get shopLatitude => 'خط العرض';

  @override
  String get shopLongitude => 'خط الطول';

  @override
  String get shopUsualOrder => 'الكمية المعتادة';

  @override
  String get shopUsualOrderHint =>
      'تُطبَّق تلقائياً عند تضمين هذا المحل في رحلة. اتركها فارغة إذا لم يكن للمحل كمية ثابتة.';

  @override
  String get shopInactive => 'غير نشط';

  @override
  String get shopNoOrder => 'لا توجد كمية معتادة';

  @override
  String shopOrderSummary(String quantity, String unit, String product) {
    return '$quantity $unit $product';
  }

  @override
  String get shopProductIncomplete => 'كل منتج يحتاج اسماً وكمية موجبة ووحدة';

  @override
  String get shopNameRequired => 'أدخل الاسم';

  @override
  String get adminActiveDrivers => 'السائقون النشطون';

  @override
  String adminLiveRides(int count) {
    return '$count رحلات نشطة';
  }

  @override
  String get adminNoRides => 'لا توجد رحلات نشطة';

  @override
  String get adminNoRidesHint => 'يظهر السائقون هنا عند بدء رحلتهم.';

  @override
  String get stateStart => 'البداية';

  @override
  String get stateVia => 'عبر';

  @override
  String get stateDestination => 'الوجهة';

  @override
  String get statePending => 'قيد الانتظار';

  @override
  String get stateArrived => 'وصل';

  @override
  String get stateDelivered => 'تم التسليم';

  @override
  String get statePartial => 'جزئي';

  @override
  String get stateFailed => 'فشل';

  @override
  String get deliveriesErpEmpty =>
      'أنشئ رحلة توصيل مُرسلة في ERPNext مع سائق، وأنشئ حساب سائق في RouteOS أولاً.';

  @override
  String get deliveriesAssignErpTitle => 'إسناد توصيل ERPNext';

  @override
  String get deliveriesMatchingDriver => 'سائق RouteOS المطابق';

  @override
  String get deliveriesDriverWarning =>
      'تحقق من السائق بعناية. سيؤدي هذا إلى ربط حساباته؛ لن تُعاد تأكيدات التسليم الحالية.';

  @override
  String get deliveriesExtraNote => 'أُدرجت في رحلة لاحقة';

  @override
  String get deliveriesAssignProductsTitle => 'إسناد المنتجات والكميات';

  @override
  String get deliveriesAssignHint =>
      'أمثلة: الحليب باللتر، العجين بالكيلوغرام، الزبادي بالأكياس. استخدم الوحدة نفسها عند تأكيد السائق للتسليم.';

  @override
  String get deliveriesUnitLabel => 'الوحدة (لتر، كجم، أكياس)';

  @override
  String get deliveriesRemoveLast => 'إزالة آخر منتج';

  @override
  String get deliveriesSyncQueued =>
      'تمت جدولة المزامنة. تعمل خلال 30 ثانية؛ حدّث لرؤية النتيجة.';

  @override
  String get deliveriesSyncBusy => 'المزامنة قيد العمل بالفعل.';

  @override
  String deliveriesSyncCounts(int synced, int failed) {
    return 'تمت مزامنة $synced، فشل $failed. يتم الاحتفاظ بالفاشلة لإعادة المحاولة.';
  }

  @override
  String deliveriesLastGps(String latitude, String longitude) {
    return 'آخر GPS: $latitude، $longitude';
  }

  @override
  String deliveriesRecordedAt(String time) {
    return 'سُجل في: $time';
  }

  @override
  String deliveriesRide(String status) {
    return 'الرحلة: $status';
  }

  @override
  String get deliveriesLinkHint =>
      'السائق: ابدأ مساراً محفوظاً برقم مركبة ERP نفسه، ثم اربط الرحلة هنا.';

  @override
  String deliveriesNote(String note) {
    return 'سند التسليم: $note';
  }

  @override
  String get deliveriesGpsNote =>
      'الوصول عبر GPS وحده لا يؤكد التسليم. لا يمكن تعديل النتائج النهائية.';

  @override
  String tripBuilderCreateFailed(String error) {
    return 'تعذّر إنشاء الرحلة: $error';
  }

  @override
  String get tripBuilderTripReferenceRequired => 'أدخل مرجع الرحلة';

  @override
  String get tripBuilderVehicleRequired => 'أدخل رقم المركبة';

  @override
  String get deliveriesRefresh => 'تحديث التوصيلات';

  @override
  String get shopRefresh => 'تحديث أسواق السوبرماركت';

  @override
  String get tabAccount => 'الحساب';

  @override
  String get routesFilterAll => 'الكل';

  @override
  String get routesTitle => 'مساراتي';

  @override
  String get routesSavedTitle => 'المسارات المحفوظة';

  @override
  String get routesEmpty =>
      'لا توجد مسارات محفوظة بعد. خطط أو سجّل مسارك الأول.';

  @override
  String get routesSearch => 'ابحث في المسارات المحفوظة';

  @override
  String get routesFavourites => 'المفضلة';

  @override
  String get routesRemoveRecent => 'إزالة من المسارات الأخيرة';

  @override
  String get routeCalculateFailed =>
      'تعذّر حساب هذا المسار. تحقق من تغطية الخريطة دون اتصال وأعد المحاولة.';

  @override
  String get routeLoadFailed =>
      'تعذّر تحميل هذا المسار. تحقق من اتصالك وأعد المحاولة.';

  @override
  String get routeTimeout =>
      'انتهت مهلة حساب المسار. تحقق من الخرائط الإقليمية وأعد المحاولة.';

  @override
  String get routeName => 'اسم المسار';

  @override
  String get routeDelete => 'حذف المسار';

  @override
  String get routeRename => 'إعادة تسمية المسار';

  @override
  String get routeShare => 'مشاركة المسار';

  @override
  String get routeOpen => 'فتح / تعديل المسار المرسوم';

  @override
  String get routeFollow => 'اتبع المسار';

  @override
  String get routeFavouriteToggle => 'تبديل المفضلة';

  @override
  String get routeSaved => 'تم حفظ المسار وهو متاح للسائقين الآخرين.';

  @override
  String get routeShared => 'تمت مشاركة المسار مع سائقي RouteOS.';

  @override
  String get drawOptimizeTitle => 'هل تريد تحسين ترتيب نقاط التوقف؟';

  @override
  String get drawOrganicsLimit =>
      'يدعم Organic Maps‏ ما يصل إلى 100 نقطة توقف إضافة إلى البداية والوجهة.';

  @override
  String get drawDriverOnly => 'رسم المسارات متاح للسائقين فقط.';

  @override
  String get drawMaxPointsReached =>
      'تم بلوغ الحد الأقصى لنقاط المسار البالغة 102.';

  @override
  String get pointDelete => 'حذف النقطة';

  @override
  String get pointInsertAfter => 'إدراج بعد';

  @override
  String get pointMoveOnMap => 'نقل على الخريطة';

  @override
  String get pointMoveEarlier => 'نقل إلى الأمام';

  @override
  String get pointMoveLater => 'نقل إلى الخلف';

  @override
  String get pointMoveTap => 'انقر على الموضع الجديد للنقطة';

  @override
  String get pointInsertTap => 'انقر لإدراج نقطة';

  @override
  String get pointEdit => 'تعديل النقطة';

  @override
  String pointLabel(int number, String type) {
    return 'نقطة $number · $type';
  }

  @override
  String get mapMyLocation => 'موقعي';

  @override
  String get mapZoomIn => 'تكبير';

  @override
  String get mapZoomOut => 'تصغير';

  @override
  String get mapDownloads => 'الخرائط دون اتصال';

  @override
  String get searchPlaces => 'ابحث عن الأماكن';

  @override
  String get vehicleSelect => 'اختر المركبة';

  @override
  String get rideStart => 'بدء الرحلة';

  @override
  String get rideEnd => 'إنهاء الرحلة';

  @override
  String get rideEndTitle => 'هل تريد إنهاء هذه الرحلة؟';

  @override
  String get rideWaitingGps => 'الرحلة نشطة — في انتظار GPS';

  @override
  String get rideWaitingGuidance => 'في انتظار توجيه GPS';

  @override
  String get rideStarting => 'يبدأ التوجيه — يرجى الانتظار.';

  @override
  String get rideLiveTrackingNote =>
      'يتوقف التتبع المباشر بعد تأكيد RouteOS انتهاء الرحلة.';

  @override
  String get rideLoadPrompt => 'حمّل المسار، اختر مركبة، وابدأ التوجيه';

  @override
  String get rideLocationMissing => 'لم يصل';

  @override
  String get rideEndNavigationFirst => 'أنهِ التوجيه قبل تعديل المسار.';

  @override
  String get recordStopSave => 'إيقاف وحفظ';

  @override
  String get recordDiscard => 'تجاهل';

  @override
  String get recordDiscardTitle => 'هل تريد تجاهل التسجيل؟';

  @override
  String get recordStopFirst => 'أوقف التسجيل أو تجاهله أولاً.';

  @override
  String get recordDiscardHint =>
      'أوقف المسجّل الأصلي وتجاهل المسار غير المحفوظ.';

  @override
  String get recordSeparateNote =>
      'يُحفظ مسار GPS الأصلي منفصلاً عن المسارات المرسومة.';

  @override
  String recordProgress(String distance) {
    return 'جارٍ تسجيل المسار · $distance';
  }

  @override
  String sessionRestoreFailed(String error) {
    return 'تعذّرت استعادة جلستك: $error';
  }

  @override
  String get screenClosed => 'أُغلقت الشاشة';

  @override
  String get loginDevelopmentAccounts => 'حسابات التطوير';

  @override
  String get actionRename => 'إعادة تسمية';

  @override
  String get adminRefreshRides => 'تحديث الرحلات النشطة';
}
