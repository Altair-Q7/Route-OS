import 'package:flutter/material.dart';
import '../l10n/generated/app_localizations.dart';

import 'delivery_reports.dart';
import 'supermarket_directory.dart';
import 'trip_builder.dart';

typedef DeliveryRequest =
    Future<dynamic> Function(String method, [Map<String, dynamic> data]);

/// Delivery requests have their own state; they never rebuild the native map.
class DeliveryPanel extends StatefulWidget {
  const DeliveryPanel({
    super.key,
    required this.request,
    required this.isAdmin,
    required this.activeRideId,
  });

  final DeliveryRequest request;
  final bool isAdmin;
  final int activeRideId;

  @override
  State<DeliveryPanel> createState() => _DeliveryPanelState();
}

class _DeliveryPanelState extends State<DeliveryPanel> {
  List<Map<String, dynamic>> assignments = [];
  List<Map<String, dynamic>> extras = [];
  bool loading = false;
  String? error;
  String? notice;
  int activeRideId = 0;

  String syncLabel(Map assignment) {
    final strings = AppStrings.of(context);
    final lastError = assignment['last_error']?.toString();
    if (lastError != null && lastError.isNotEmpty) {
      return strings.deliveriesSyncError(lastError);
    }
    if (assignment['sync_pending'] == true) {
      return strings.deliveriesSyncPending;
    }
    final value = assignment['last_sync']?.toString();
    if (value == null || value.isEmpty) return strings.deliveriesSyncNotSynced;
    try {
      final date = DateTime.parse(value).toLocal();
      final material = MaterialLocalizations.of(context);
      final formatted =
          '${material.formatMediumDate(date)} ${material.formatTimeOfDay(TimeOfDay.fromDateTime(date))}';
      return strings.deliveriesSyncLast(formatted);
    } catch (_) {
      return strings.deliveriesSyncLast(value);
    }
  }

  String shortAddress(Object? value) {
    final lines =
        value
            ?.toString()
            .split('\n')
            .map((line) => line.trim())
            .where((line) => line.isNotEmpty)
            .toList() ??
        <String>[];
    if (lines.length <= 2) return lines.join(', ');
    return '${lines.first}, ${lines[1]}';
  }

  String statusLabel(Object? value) {
    final strings = AppStrings.of(context);
    switch (value?.toString().toLowerCase()) {
      case 'pending':
        return strings.statePending;
      case 'arrived':
        return strings.stateArrived;
      case 'delivered':
        return strings.stateDelivered;
      case 'partial':
        return strings.statePartial;
      case 'failed':
        return strings.stateFailed;
      default:
        return strings.stateUnknown;
    }
  }

  String actionLabel(String status) {
    final strings = AppStrings.of(context);
    switch (status) {
      case 'arrived':
        return strings.deliveryActionArrived;
      case 'delivered':
        return strings.deliveryActionDelivered;
      case 'partial':
        return strings.deliveryActionPartial;
      case 'failed':
        return strings.deliveryActionFailed;
      default:
        return strings.deliveryActionUpdate;
    }
  }

  bool isCompleted(Map stop) {
    final status = stop['status']?.toString().toLowerCase();
    return status == 'delivered' || status == 'partial' || status == 'failed';
  }

  String nextAction(Map assignment) {
    final strings = AppStrings.of(context);
    final stops = (assignment['stops'] as List).cast<Map>();
    Map? next;
    for (final stop in stops) {
      if (!isCompleted(stop)) {
        next = stop;
        break;
      }
    }
    if (next == null) {
      return strings.deliveriesNextComplete;
    }
    final customer = '${next['customer'] ?? next['address']}';
    if (assignment['ride_id'] == null) {
      return widget.isAdmin
          ? strings.deliveriesNextLinkRideAdmin
          : strings.deliveriesNextLinkRideDriver(
              assignment['vehicle'].toString(),
            );
    }
    if (next['status'] == 'arrived') {
      return strings.deliveriesNextConfirm(customer);
    }
    return strings.deliveriesNextDrive(customer);
  }

  @override
  void initState() {
    super.initState();
    activeRideId = widget.activeRideId;
    perform(load);
  }

  Future<void> load() async {
    final results = await Future.wait([
      widget.request('deliveries'),
      widget.request('session'),
    ]);
    final result = results[0] as Map;
    final session = results[1] as Map;
    var pendingExtras = <Map<String, dynamic>>[];
    // Admin-only; drivers simply have no extras to see.
    if (widget.isAdmin) {
      try {
        final requested = await widget.request('delivery.extras') as Map;
        pendingExtras = (requested['extras'] as List)
            .map((item) => Map<String, dynamic>.from(item as Map))
            .toList();
      } catch (_) {
        pendingExtras = <Map<String, dynamic>>[];
      }
    }
    if (mounted) {
      setState(() {
        assignments = (result['assignments'] as List)
            .map((item) => Map<String, dynamic>.from(item as Map))
            .toList();
        extras = pendingExtras;
        activeRideId = (session['active_ride_id'] as num? ?? 0).toInt();
      });
    }
  }

  Future<void> perform(Future<void> Function() action) async {
    if (loading) return;
    setState(() {
      loading = true;
      error = null;
      notice = null;
    });
    try {
      await action();
    } catch (failure) {
      if (mounted) setState(() => error = failure.toString());
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> importTrip() async {
    final catalog = await widget.request('erpnext.catalog') as Map;
    if (!mounted) return;
    final trips = catalog['trips'] as List;
    final drivers = catalog['drivers'] as List;
    if (trips.isEmpty || drivers.isEmpty) {
      setState(() => notice = AppStrings.of(context).deliveriesErpEmpty);
      return;
    }
    String trip = trips.first['name'] as String;
    int driver = (drivers.first['id'] as num).toInt();
    final selected = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, update) => AlertDialog(
          title: Text(AppStrings.of(context).deliveriesAssignErpTitle),
          content: SizedBox(
            width: 400,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                DropdownButtonFormField<String>(
                  initialValue: trip,
                  isExpanded: true,
                  decoration: InputDecoration(
                    labelText: AppStrings.of(context).deliveriesErpTrip,
                  ),
                  items: [
                    for (final item in trips)
                      DropdownMenuItem(
                        value: item['name'] as String,
                        child: Text(
                          '${item['name']} · ${item['driver_name'] ?? item['driver']}',
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                  ],
                  onChanged: (value) {
                    if (value != null) update(() => trip = value);
                  },
                ),
                DropdownButtonFormField<int>(
                  initialValue: driver,
                  decoration: InputDecoration(
                    labelText: AppStrings.of(context).deliveriesMatchingDriver,
                  ),
                  items: [
                    for (final item in drivers)
                      DropdownMenuItem(
                        value: (item['id'] as num).toInt(),
                        child: Text(item['name'] as String),
                      ),
                  ],
                  onChanged: (value) {
                    if (value != null) update(() => driver = value);
                  },
                ),
                SizedBox(height: 12),
                Text(AppStrings.of(context).deliveriesDriverWarning),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: Text(AppStrings.of(context).actionCancel),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: Text(AppStrings.of(context).actionAssign),
            ),
          ],
        ),
      ),
    );
    if (selected != true || !mounted) return;
    await widget.request('erpnext.import', {'trip': trip, 'driver_id': driver});
    await load();
  }

  Future<void> confirmStop(
    Map<String, dynamic> assignment,
    Map stop,
    String status,
  ) async {
    String reason = '';
    String extra = '';
    final form = GlobalKey<FormState>();
    final products = (stop['items'] as List? ?? []).cast<Map>();
    final quantities = {for (final item in products) item['id'] as String: '0'};
    final recordsProducts = status == 'delivered' || status == 'partial';
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, update) => AlertDialog(
          title: Text(
            status == 'delivered'
                ? AppStrings.of(context).confirmTitleDelivered
                : status == 'partial'
                ? AppStrings.of(context).confirmTitlePartial
                : status == 'failed'
                ? AppStrings.of(context).confirmTitleFailed
                : AppStrings.of(context).confirmTitleArrived,
          ),
          scrollable: true,
          content: Form(
            key: form,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  '${stop['customer'] ?? stop['address']}\n'
                  '${AppStrings.of(context).deliveriesGpsNote}',
                ),
                if (recordsProducts && products.isEmpty)
                  Text(AppStrings.of(context).confirmNoProducts),
                if (recordsProducts)
                  for (final item in products)
                    TextFormField(
                      initialValue: '0',
                      keyboardType: const TextInputType.numberWithOptions(
                        decimal: true,
                      ),
                      decoration: InputDecoration(
                        labelText: AppStrings.of(context).confirmDeliveredLabel(
                          item['product_name'].toString(),
                          item['uom'].toString(),
                        ),
                        helperText: AppStrings.of(context).confirmAssigned(
                          item['planned_quantity'].toString(),
                          item['uom'].toString(),
                        ),
                      ),
                      validator: (value) {
                        final qty = num.tryParse(value ?? '');
                        final planned = num.parse(
                          item['planned_quantity'].toString(),
                        );
                        if (qty == null ||
                            !qty.isFinite ||
                            qty < 0 ||
                            qty > planned ||
                            !RegExp(
                              r'^(?:[0-9]+(?:\.[0-9]{1,3})?|\.[0-9]{1,3})$',
                            ).hasMatch(value ?? '')) {
                          return AppStrings.of(
                            context,
                          ).confirmQuantityRange(planned.toString());
                        }
                        if (status == 'delivered' && qty != planned) {
                          return AppStrings.of(context).confirmUsePartial;
                        }
                        return null;
                      },
                      onChanged: (value) =>
                          quantities[item['id'] as String] = value,
                    ),
                if (recordsProducts)
                  Padding(
                    padding: const EdgeInsets.only(top: 12),
                    child: TextFormField(
                      initialValue: '',
                      keyboardType: const TextInputType.numberWithOptions(
                        decimal: true,
                      ),
                      decoration: InputDecoration(
                        labelText: AppStrings.of(context).confirmExtraLabel,
                        helperText: AppStrings.of(context).confirmExtraHint,
                      ),
                      validator: (value) {
                        final text = (value ?? '').trim();
                        if (text.isEmpty) return null;
                        final qty = num.tryParse(text);
                        if (qty == null ||
                            !qty.isFinite ||
                            qty <= 0 ||
                            !RegExp(
                              r'^(?:[0-9]+(?:\.[0-9]{1,3})?|\.[0-9]{1,3})$',
                            ).hasMatch(text)) {
                          return AppStrings.of(context).confirmExtraPositive;
                        }
                        return null;
                      },
                      onChanged: (value) => extra = value.trim(),
                    ),
                  ),
                if (status == 'failed' || status == 'partial')
                  TextFormField(
                    maxLength: 500,
                    decoration: InputDecoration(
                      labelText: status == 'partial'
                          ? AppStrings.of(context).confirmPartialReason
                          : AppStrings.of(context).confirmFailedReason,
                    ),
                    validator: (value) => (value ?? '').trim().isEmpty
                        ? AppStrings.of(context).confirmReasonRequired
                        : null,
                    onChanged: (value) => update(() => reason = value.trim()),
                  ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: Text(AppStrings.of(context).actionCancel),
            ),
            FilledButton(
              onPressed: recordsProducts && products.isEmpty
                  ? null
                  : () {
                      if (form.currentState!.validate()) {
                        Navigator.pop(context, true);
                      }
                    },
              child: Text(AppStrings.of(context).actionConfirm),
            ),
          ],
        ),
      ),
    );
    if (confirmed != true || !mounted) return;
    await widget.request('delivery.confirm', {
      'id': assignment['id'],
      'stop_id': stop['id'],
      'status': status,
      'reason': reason,
      'items': recordsProducts
          ? [
              for (final item in products)
                {
                  'id': item['id'],
                  'delivered_quantity': quantities[item['id']],
                },
            ]
          : [],
      // The shop's request for more is recorded for a later trip, not handed over.
      'extras': recordsProducts && extra.isNotEmpty && products.isNotEmpty
          ? [
              {
                'product_name': products.first['product_name'],
                'uom': products.first['uom'],
                'quantity': extra,
              },
            ]
          : [],
    });
    await load();
  }

  /// Closes extra requests once they are planned into a trip or moved to another shop.
  Future<void> resolveExtras(Map<String, dynamic> extra) async {
    await perform(() async {
      await widget.request('delivery.extras.resolve', {
        'ids': extra['ids'],
        'note': AppStrings.of(context).deliveriesExtraNote,
      });
      await load();
      if (mounted) {
        setState(
          () => notice = AppStrings.of(context).deliveriesExtraResolved(
            extra['customer'].toString(),
            extra['quantity'].toString(),
            extra['uom'].toString(),
            extra['product_name'].toString(),
          ),
        );
      }
    });
  }

  /// Moves planned batter between two shops so nothing is left on the van.
  Future<void> transfer(Map<String, dynamic> assignment) async {
    final pending = [
      for (final stop in assignment['stops'] as List)
        if ((stop['status'] == 'pending' || stop['status'] == 'arrived')) stop,
    ];
    if (pending.length < 2) {
      setState(() => notice = AppStrings.of(context).transferNeedsTwoStops);
      return;
    }
    var from = pending.first;
    var to = pending[1];
    final products = <Map<String, dynamic>>[
      for (final item in (from['items'] as List? ?? []))
        Map<String, dynamic>.from(item as Map),
    ];
    if (products.isEmpty) return;
    var chosen = products.first;
    final quantity = TextEditingController();

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, update) => AlertDialog(
          title: Text(AppStrings.of(context).transferTitle),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(AppStrings.of(context).transferHint),
              SizedBox(height: 12),
              DropdownButtonFormField<String>(
                initialValue: from['id'],
                isExpanded: true,
                decoration: InputDecoration(
                  labelText: AppStrings.of(context).transferFrom,
                ),
                items: [
                  for (final stop in pending)
                    DropdownMenuItem(
                      value: stop['id'],
                      child: Text(
                        '${stop['customer']}',
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                ],
                onChanged: (value) => update(() {
                  from = pending.firstWhere((stop) => stop['id'] == value);
                  chosen = (from['items'] as List).first;
                }),
              ),
              DropdownButtonFormField<String>(
                initialValue: to['id'],
                isExpanded: true,
                decoration: InputDecoration(
                  labelText: AppStrings.of(context).transferTo,
                ),
                items: [
                  for (final stop in pending)
                    DropdownMenuItem(
                      value: stop['id'],
                      child: Text(
                        '${stop['customer']}',
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                ],
                onChanged: (value) => update(
                  () => to = pending.firstWhere((stop) => stop['id'] == value),
                ),
              ),
              DropdownButtonFormField<String>(
                initialValue: chosen['product_name'].toString(),
                isExpanded: true,
                decoration: InputDecoration(
                  labelText: AppStrings.of(context).tripBuilderProduct,
                ),
                items: [
                  for (final item in products)
                    DropdownMenuItem(
                      value: item['product_name'].toString(),
                      child: Text(
                        AppStrings.of(context).transferProductOption(
                          item['product_name'].toString(),
                          item['planned_quantity'].toString(),
                          item['uom'].toString(),
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                ],
                onChanged: (value) => update(() {
                  chosen = products.firstWhere(
                    (item) => item['product_name'].toString() == value,
                  );
                }),
              ),
              TextField(
                controller: quantity,
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
                decoration: InputDecoration(
                  labelText: AppStrings.of(
                    context,
                  ).transferQuantity(chosen['uom'].toString()),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: Text(AppStrings.of(context).actionCancel),
            ),
            FilledButton(
              onPressed: () {
                final amount = double.tryParse(quantity.text.trim());
                if (amount == null || amount <= 0) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(AppStrings.of(context).transferPositive),
                    ),
                  );
                  return;
                }
                Navigator.pop(ctx, true);
              },
              child: Text(AppStrings.of(context).transferMove),
            ),
          ],
        ),
      ),
    );
    if (confirmed != true || !mounted) {
      quantity.dispose();
      return;
    }
    await perform(() async {
      await widget.request('delivery.transfer', {
        'id': assignment['id'],
        'from_stop_id': from['id'],
        'to_stop_id': to['id'],
        'product_name': chosen['product_name'],
        'uom': chosen['uom'],
        'quantity': quantity.text.trim(),
      });
      quantity.dispose();
      await load();
    });
  }

  Future<void> assignProducts(Map assignment, Map stop) async {
    final form = GlobalKey<FormState>();
    final rows = <Map<String, String>>[
      for (final item in stop['items'] as List? ?? [])
        {
          'product_name': item['product_name'].toString(),
          'planned_quantity': item['planned_quantity'].toString(),
          'uom': item['uom'].toString(),
        },
    ];
    if (rows.isEmpty) {
      rows.add({'product_name': '', 'planned_quantity': '', 'uom': ''});
    }
    final accepted = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, update) => AlertDialog(
          title: Text(AppStrings.of(context).deliveriesAssignProductsTitle),
          scrollable: true,
          content: Form(
            key: form,
            child: SizedBox(
              width: 400,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(AppStrings.of(context).deliveriesAssignHint),
                  for (int i = 0; i < rows.length; i++)
                    Padding(
                      padding: const EdgeInsets.only(top: 12),
                      child: Column(
                        children: [
                          TextFormField(
                            initialValue: rows[i]['product_name'],
                            maxLength: 140,
                            decoration: InputDecoration(
                              labelText:
                                  '${AppStrings.of(context).tripBuilderProduct} ${i + 1}',
                            ),
                            validator: (value) => (value ?? '').trim().isEmpty
                                ? AppStrings.of(context).tripBuilderProduct
                                : null,
                            onChanged: (value) =>
                                rows[i]['product_name'] = value.trim(),
                          ),
                          TextFormField(
                            initialValue: rows[i]['planned_quantity'],
                            keyboardType: const TextInputType.numberWithOptions(
                              decimal: true,
                            ),
                            decoration: InputDecoration(
                              labelText: AppStrings.of(
                                context,
                              ).tripBuilderQuantity,
                            ),
                            validator: (value) {
                              final qty = num.tryParse(value ?? '');
                              return qty == null || !qty.isFinite || qty <= 0
                                  ? AppStrings.of(context).transferPositive
                                  : null;
                            },
                            onChanged: (value) =>
                                rows[i]['planned_quantity'] = value,
                          ),
                          TextFormField(
                            initialValue: rows[i]['uom'],
                            maxLength: 40,
                            decoration: InputDecoration(
                              labelText: AppStrings.of(
                                context,
                              ).deliveriesUnitLabel,
                            ),
                            validator: (value) => (value ?? '').trim().isEmpty
                                ? AppStrings.of(context).tripBuilderEnterUnit
                                : null,
                            onChanged: (value) => rows[i]['uom'] = value.trim(),
                          ),
                        ],
                      ),
                    ),
                  TextButton(
                    onPressed: rows.length >= 100
                        ? null
                        : () => update(
                            () => rows.add({
                              'product_name': '',
                              'planned_quantity': '',
                              'uom': '',
                            }),
                          ),
                    child: Text(AppStrings.of(context).tripBuilderAddProduct),
                  ),
                  if (rows.length > 1)
                    TextButton(
                      onPressed: () => update(() => rows.removeLast()),
                      child: Text(AppStrings.of(context).deliveriesRemoveLast),
                    ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: Text(AppStrings.of(context).actionCancel),
            ),
            FilledButton(
              onPressed: () {
                if (form.currentState!.validate()) Navigator.pop(context, true);
              },
              child: Text(AppStrings.of(context).actionSave),
            ),
          ],
        ),
      ),
    );
    if (accepted != true || !mounted) return;
    await widget.request('delivery.products', {
      'id': assignment['id'],
      'stop_id': stop['id'],
      'items': rows,
    });
    await load();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Text(AppStrings.of(context).deliveriesTitle),
      actions: [
        IconButton(
          tooltip: AppStrings.of(context).deliveriesRefresh,
          onPressed: loading ? null : () => perform(load),
          icon: const Icon(Icons.refresh),
        ),
      ],
    ),
    body: Column(
      children: [
        if (loading) const LinearProgressIndicator(),
        if (error != null)
          Padding(padding: const EdgeInsets.all(12), child: Text(error!)),
        if (notice != null)
          Padding(padding: const EdgeInsets.all(12), child: Text(notice!)),
        if (widget.isAdmin)
          Wrap(
            spacing: 12,
            children: [
              FilledButton.icon(
                onPressed: loading
                    ? null
                    : () async {
                        final created = await Navigator.of(context).push<bool>(
                          MaterialPageRoute(
                            builder: (_) =>
                                TripBuilder(request: widget.request),
                          ),
                        );
                        if (created == true && mounted) {
                          setState(
                            () => notice = AppStrings.of(
                              context,
                            ).tripBuilderCreated,
                          );
                          await load();
                        }
                      },
                icon: const Icon(Icons.add),
                label: Text(AppStrings.of(context).deliveriesCreateTrip),
              ),
              FilledButton.icon(
                onPressed: loading ? null : () => perform(importTrip),
                icon: const Icon(Icons.sync_alt),
                label: Text(AppStrings.of(context).deliveriesAssignErp),
              ),
              OutlinedButton(
                onPressed: loading
                    ? null
                    : () => perform(() async {
                        final result =
                            await widget.request('erpnext.sync') as Map;
                        await load();
                        if (mounted) {
                          setState(
                            () => notice = result['queued'] == true
                                ? AppStrings.of(context).deliveriesSyncQueued
                                : result['busy'] == true
                                ? AppStrings.of(context).deliveriesSyncBusy
                                : AppStrings.of(context).deliveriesSyncCounts(
                                    (result['synced'] as num).toInt(),
                                    (result['failed'] as num).toInt(),
                                  ),
                          );
                        }
                      }),
                child: Text(AppStrings.of(context).deliveriesSyncErp),
              ),
              OutlinedButton.icon(
                onPressed: loading
                    ? null
                    : () => Navigator.of(context).push<void>(
                        MaterialPageRoute(
                          builder: (_) =>
                              SupermarketDirectory(request: widget.request),
                        ),
                      ),
                icon: const Icon(Icons.storefront_outlined),
                label: Text(AppStrings.of(context).shopTitle),
              ),
              OutlinedButton.icon(
                onPressed: loading
                    ? null
                    : () => Navigator.of(context).push<void>(
                        MaterialPageRoute(
                          builder: (_) =>
                              DeliveryReports(request: widget.request),
                        ),
                      ),
                icon: const Icon(Icons.assessment_outlined),
                label: Text(AppStrings.of(context).reportsTitle),
              ),
            ],
          ),
        Expanded(
          child: ListView(
            padding: const EdgeInsets.all(12),
            children: [
              if (widget.isAdmin && extras.isNotEmpty) ...[
                Text(
                  AppStrings.of(context).deliveriesExtraTitle,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                Text(AppStrings.of(context).deliveriesExtraHint),
                SizedBox(height: 8),
                for (final extra in extras)
                  Card(
                    child: ListTile(
                      title: Text(
                        AppStrings.of(context).deliveriesExtraRequest(
                          extra['customer'].toString(),
                          extra['quantity'].toString(),
                          extra['uom'].toString(),
                          extra['product_name'].toString(),
                        ),
                      ),
                      subtitle: Text(
                        extra['requests'] == 1
                            ? AppStrings.of(context).deliveriesExtraRecorded
                            : AppStrings.of(
                                context,
                              ).deliveriesExtraRecordedMany(
                                (extra['requests'] as num).toInt(),
                              ),
                      ),
                      trailing: TextButton(
                        onPressed: loading ? null : () => resolveExtras(extra),
                        child: Text(
                          AppStrings.of(context).deliveriesExtraPlanned,
                        ),
                      ),
                    ),
                  ),
                SizedBox(height: 16),
              ],
              if (assignments.isEmpty && !loading)
                ListTile(
                  title: Text(AppStrings.of(context).deliveriesEmpty),
                  subtitle: Text(AppStrings.of(context).deliveriesEmptyHint),
                ),
              for (final assignment in assignments)
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${assignment['trip']} · ${assignment['status']}',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        Text(
                          '${assignment['driver_name']} · ${assignment['vehicle']}',
                        ),
                        Text(syncLabel(assignment)),
                        Text(
                          AppStrings.of(context).deliveriesStopsCompleted(
                            (assignment['stops'] as List)
                                .where((stop) => isCompleted(stop as Map))
                                .length,
                            (assignment['stops'] as List).length,
                          ),
                        ),
                        Text(nextAction(assignment)),
                        if (assignment['location'] != null)
                          Text.rich(
                            TextSpan(
                              children: [
                                TextSpan(
                                  text: AppStrings.of(context)
                                      .deliveriesLastGps(
                                        assignment['location']['latitude']
                                            .toString(),
                                        assignment['location']['longitude']
                                            .toString(),
                                      ),
                                ),
                                const TextSpan(text: '\n'),
                                TextSpan(
                                  text: AppStrings.of(context)
                                      .deliveriesRecordedAt(
                                        assignment['location']['recorded_at']
                                            .toString(),
                                      ),
                                ),
                              ],
                            ),
                          ),
                        if (assignment['ride'] != null)
                          Text(
                            AppStrings.of(context).deliveriesRide(
                              assignment['ride']['status'].toString(),
                            ),
                          ),
                        if (assignment['ride_id'] == null && !widget.isAdmin)
                          OutlinedButton(
                            onPressed: loading || activeRideId == 0
                                ? null
                                : () => perform(() async {
                                    await widget.request('delivery.ride', {
                                      'id': assignment['id'],
                                      'ride_id': activeRideId,
                                    });
                                    await load();
                                  }),
                            child: Text(
                              AppStrings.of(context).deliveriesLinkRide,
                            ),
                          ),
                        if ((assignment['surplus'] as List? ?? []).isNotEmpty &&
                            assignment['ride_id'] == null)
                          Padding(
                            padding: const EdgeInsets.only(top: 8),
                            child: Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    AppStrings.of(
                                      context,
                                    ).deliveriesStillToHandOver(
                                      (assignment['surplus'] as List)
                                          .map(
                                            (item) =>
                                                '${item['quantity']} ${item['uom']} ${item['product_name']}',
                                          )
                                          .join(', '),
                                    ),
                                    style: Theme.of(
                                      context,
                                    ).textTheme.bodySmall,
                                  ),
                                ),
                                TextButton(
                                  onPressed: loading
                                      ? null
                                      : () =>
                                            perform(() => transfer(assignment)),
                                  child: Text(
                                    AppStrings.of(context).deliveriesMoveBatter,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        for (final stop in assignment['stops'] as List)
                          Card(
                            margin: const EdgeInsets.only(top: 12),
                            child: Padding(
                              padding: const EdgeInsets.all(12),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Expanded(
                                        child: Text(
                                          '${stop['customer'] ?? stop['address']}',
                                          style: Theme.of(
                                            context,
                                          ).textTheme.titleSmall,
                                        ),
                                      ),
                                      Chip(
                                        label: Text(
                                          statusLabel(stop['status']),
                                        ),
                                      ),
                                    ],
                                  ),
                                  if (shortAddress(
                                    stop['address_text'],
                                  ).isNotEmpty)
                                    Text(
                                      shortAddress(stop['address_text']),
                                      style: Theme.of(
                                        context,
                                      ).textTheme.bodySmall,
                                    ),
                                  if (stop['delivery_note'] != null)
                                    Text(
                                      AppStrings.of(context).deliveriesNote(
                                        stop['delivery_note'].toString(),
                                      ),
                                    ),
                                  for (final item
                                      in stop['items'] as List? ?? [])
                                    Text(
                                      AppStrings.of(
                                        context,
                                      ).confirmDeliveredSummary(
                                        item['product_name'].toString(),
                                        item['delivered_quantity'].toString(),
                                        item['planned_quantity'].toString(),
                                        item['uom'].toString(),
                                      ),
                                    ),
                                  if (widget.isAdmin &&
                                      assignment['ride_id'] == null &&
                                      stop['status'] == 'pending' &&
                                      stop['delivery_note'] == null)
                                    OutlinedButton(
                                      onPressed: loading
                                          ? null
                                          : () => perform(
                                              () => assignProducts(
                                                assignment,
                                                stop as Map,
                                              ),
                                            ),
                                      child: Text(
                                        AppStrings.of(
                                          context,
                                        ).deliveriesAssignProducts,
                                      ),
                                    ),
                                  if ((stop['reason'] as String).isNotEmpty)
                                    Text(
                                      AppStrings.of(context).deliveriesReason(
                                        stop['reason'].toString(),
                                      ),
                                    ),
                                  if (assignment['ride_id'] != null &&
                                      stop['status'] != 'delivered' &&
                                      stop['status'] != 'partial' &&
                                      stop['status'] != 'failed')
                                    Wrap(
                                      spacing: 8,
                                      children: [
                                        for (final status in [
                                          'arrived',
                                          'delivered',
                                          'partial',
                                          'failed',
                                        ])
                                          OutlinedButton(
                                            onPressed: loading
                                                ? null
                                                : () => perform(
                                                    () => confirmStop(
                                                      assignment,
                                                      stop as Map,
                                                      status,
                                                    ),
                                                  ),
                                            child: Text(actionLabel(status)),
                                          ),
                                      ],
                                    ),
                                ],
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                ),
            ],
          ),
        ),
      ],
    ),
  );
}
