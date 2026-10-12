import 'package:flutter/material.dart';

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

  @override
  void initState() {
    super.initState();
    activeRideId = widget.activeRideId;
    perform(load);
  }

  Future<void> load() async {
    final result = await widget.request('deliveries') as Map;
    final session = await widget.request('session') as Map;
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
      setState(
        () => notice =
            'Create a submitted delivery trip with a driver '
            'in ERPNext, and a driver account in RouteOS, first.',
      );
      return;
    }
    String trip = trips.first['name'] as String;
    int driver = (drivers.first['id'] as num).toInt();
    final selected = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, update) => AlertDialog(
          title: const Text('Assign ERPNext delivery'),
          content: SizedBox(
            width: 400,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                DropdownButtonFormField<String>(
                  initialValue: trip,
                  isExpanded: true,
                  decoration: const InputDecoration(labelText: 'ERPNext trip'),
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
                  decoration: const InputDecoration(
                    labelText: 'Matching RouteOS driver',
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
                const SizedBox(height: 12),
                const Text(
                  'Check the driver carefully. This links their accounts; '
                  'existing delivery confirmations will not be reset.',
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Assign'),
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
                ? 'Confirm delivered?'
                : status == 'partial'
                ? 'Record partial delivery?'
                : status == 'failed'
                ? 'Record failed delivery?'
                : 'Record arrival?',
          ),
          scrollable: true,
          content: Form(
            key: form,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  '${stop['customer'] ?? stop['address']}\n'
                  'GPS arrival alone does not confirm delivery. Final outcomes cannot be overwritten.',
                ),
                if (recordsProducts && products.isEmpty)
                  const Text(
                    'No products assigned. Ask the admin to add the products and quantities first.',
                  ),
                if (recordsProducts)
                  for (final item in products)
                    TextFormField(
                      initialValue: '0',
                      keyboardType: const TextInputType.numberWithOptions(
                        decimal: true,
                      ),
                      decoration: InputDecoration(
                        labelText:
                            '${item['product_name']} delivered (${item['uom']})',
                        helperText:
                            'Assigned: ${item['planned_quantity']} ${item['uom']}',
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
                          return 'Enter 0 to $planned, with up to 3 decimal places';
                        }
                        if (status == 'delivered' && qty != planned) {
                          return 'For a shortage, cancel and choose partial delivery';
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
                        labelText: 'Extra this shop asked for next trip',
                        helperText:
                            'Recorded only. Nothing extra is handed over now.',
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
                          return 'Enter a positive quantity with up to 3 decimals';
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
                          ? 'Reason for shortage'
                          : 'Why did delivery fail?',
                    ),
                    validator: (value) => (value ?? '').trim().isEmpty
                        ? 'A reason is required'
                        : null,
                    onChanged: (value) => update(() => reason = value.trim()),
                  ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: recordsProducts && products.isEmpty
                  ? null
                  : () {
                      if (form.currentState!.validate()) {
                        Navigator.pop(context, true);
                      }
                    },
              child: const Text('Confirm'),
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
        'note': 'Planned into a later trip',
      });
      await load();
      if (mounted) {
        setState(
          () => notice =
              '${extra['customer']} no longer waiting on ${extra['quantity']} ${extra['uom']} ${extra['product_name']}.',
        );
      }
    });
  }

  /// Moves planned batter between two shops so nothing is left on the van.
  Future<void> transfer(Map<String, dynamic> assignment) async {
    final pending = [
      for (final stop in assignment['stops'] as List)
        if ((stop['status'] == 'pending' || stop['status'] == 'arrived'))
          stop,
    ];
    if (pending.length < 2) {
      setState(() => notice = 'Add at least two unconfirmed shops before moving batter.');
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
          title: const Text('Move batter between shops'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'Batter a shop will not take can go to another shop on this trip '
                'instead of being left over. The driver still hands over only the plan.',
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                initialValue: from['id'],
                isExpanded: true,
                decoration: const InputDecoration(labelText: 'Take from'),
                items: [
                  for (final stop in pending)
                    DropdownMenuItem(
                      value: stop['id'],
                      child: Text('${stop['customer']}',
                          overflow: TextOverflow.ellipsis),
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
                decoration: const InputDecoration(labelText: 'Give to'),
                items: [
                  for (final stop in pending)
                    DropdownMenuItem(
                      value: stop['id'],
                      child: Text('${stop['customer']}',
                          overflow: TextOverflow.ellipsis),
                    ),
                ],
                onChanged: (value) => update(
                  () => to = pending.firstWhere((stop) => stop['id'] == value),
                ),
              ),
              DropdownButtonFormField<String>(
                initialValue: chosen['product_name'].toString(),
                isExpanded: true,
                decoration: const InputDecoration(labelText: 'Product'),
                items: [
                  for (final item in products)
                    DropdownMenuItem(
                      value: item['product_name'].toString(),
                      child: Text(
                        '${item['product_name']} (planned ${item['planned_quantity']} ${item['uom']})',
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
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
                decoration: InputDecoration(
                  labelText: 'How much to move (${chosen['uom']})',
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () {
                final amount = double.tryParse(quantity.text.trim());
                if (amount == null || amount <= 0) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Enter a positive quantity')),
                  );
                  return;
                }
                Navigator.pop(ctx, true);
              },
              child: const Text('Move'),
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
          title: const Text('Assign products and quantities'),
          scrollable: true,
          content: Form(
            key: form,
            child: SizedBox(
              width: 400,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text(
                    'Examples: Milk in litres, Batter in kg, Curd in packets. '
                    'Use the same unit when the driver confirms delivery.',
                  ),
                  for (int i = 0; i < rows.length; i++)
                    Padding(
                      padding: const EdgeInsets.only(top: 12),
                      child: Column(
                        children: [
                          TextFormField(
                            initialValue: rows[i]['product_name'],
                            maxLength: 140,
                            decoration: InputDecoration(
                              labelText: 'Product ${i + 1}',
                            ),
                            validator: (value) => (value ?? '').trim().isEmpty
                                ? 'Enter a product name'
                                : null,
                            onChanged: (value) =>
                                rows[i]['product_name'] = value.trim(),
                          ),
                          TextFormField(
                            initialValue: rows[i]['planned_quantity'],
                            keyboardType: const TextInputType.numberWithOptions(
                              decimal: true,
                            ),
                            decoration: const InputDecoration(
                              labelText: 'Assigned quantity',
                            ),
                            validator: (value) {
                              final qty = num.tryParse(value ?? '');
                              return qty == null || !qty.isFinite || qty <= 0
                                  ? 'Enter a positive quantity'
                                  : null;
                            },
                            onChanged: (value) =>
                                rows[i]['planned_quantity'] = value,
                          ),
                          TextFormField(
                            initialValue: rows[i]['uom'],
                            maxLength: 40,
                            decoration: const InputDecoration(
                              labelText: 'Unit (L, kg, packets, etc.)',
                            ),
                            validator: (value) => (value ?? '').trim().isEmpty
                                ? 'Enter a unit'
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
                    child: const Text('Add product'),
                  ),
                  if (rows.length > 1)
                    TextButton(
                      onPressed: () => update(() => rows.removeLast()),
                      child: const Text('Remove last product'),
                    ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () {
                if (form.currentState!.validate()) Navigator.pop(context, true);
              },
              child: const Text('Save products'),
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
      title: const Text('Deliveries'),
      actions: [
        IconButton(
          tooltip: 'Refresh deliveries',
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
                            builder: (_) => TripBuilder(request: widget.request),
                          ),
                        );
                        if (created == true && mounted) {
                          setState(
                            () => notice =
                                'Trip created and assigned to the driver.',
                          );
                          await load();
                        }
                      },
                icon: const Icon(Icons.add),
                label: const Text('Create trip'),
              ),
              FilledButton.icon(
                onPressed: loading ? null : () => perform(importTrip),
                icon: const Icon(Icons.sync_alt),
                label: const Text('Assign ERPNext trip'),
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
                                ? 'Sync queued. It runs within 30 seconds; refresh to see the result.'
                                : result['busy'] == true
                                ? 'Sync is already running.'
                                : '${result['synced']} synced, ${result['failed']} failed. Failed updates are kept for retry.',
                          );
                        }
                      }),
                child: const Text('Sync to ERPNext'),
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
                label: const Text('Supermarkets'),
              ),
            ],
          ),
        Expanded(
          child: ListView(
            padding: const EdgeInsets.all(12),
            children: [
              if (widget.isAdmin && extras.isNotEmpty) ...[
                Text(
                  'Extra requested by shops',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const Text(
                  'Drivers handed over only the plan. Build these into a later trip, '
                  'or give them to another shop so nothing is left over.',
                ),
                const SizedBox(height: 8),
                for (final extra in extras)
                  Card(
                    child: ListTile(
                      title: Text(
                        '${extra['customer']} asked for ${extra['quantity']} ${extra['uom']} '
                        '${extra['product_name']}',
                      ),
                      subtitle: Text(
                        extra['requests'] == 1
                            ? 'Recorded once'
                            : 'Recorded ${extra['requests']} times',
                      ),
                      trailing: TextButton(
                        onPressed: loading ? null : () => resolveExtras(extra),
                        child: const Text('Planned'),
                      ),
                    ),
                  ),
                const SizedBox(height: 16),
              ],
              if (assignments.isEmpty && !loading)
                const ListTile(
                  title: Text('No delivery assignments'),
                  subtitle: Text(
                    'An admin can create a trip here, or import an ERPNext '
                    'delivery trip. Drivers only see their own assignments.',
                  ),
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
                        Text(
                          'ERP sync: ${assignment['last_error'] ?? (assignment['sync_pending'] == true ? 'Pending' : assignment['last_sync'] ?? 'Not synced')}',
                        ),
                        if (assignment['location'] != null)
                          Text(
                            'Last GPS: ${assignment['location']['latitude']}, ${assignment['location']['longitude']}\n'
                            'Recorded: ${assignment['location']['recorded_at']}',
                          ),
                        if (assignment['ride'] != null)
                          Text('Ride: ${assignment['ride']['status']}'),
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
                            child: const Text('Link my current ride'),
                          ),
                        if (assignment['ride_id'] == null)
                          const Text(
                            'Driver: start a saved route using the ERP vehicle number, then link the ride here.',
                          ),
                        if ((assignment['surplus'] as List? ?? []).isNotEmpty &&
                            assignment['ride_id'] == null)
                          Padding(
                            padding: const EdgeInsets.only(top: 8),
                            child: Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    'Still to hand over: ${(assignment['surplus'] as List).map((item) => '${item['quantity']} ${item['uom']} ${item['product_name']}').join(', ')}',
                                    style: Theme.of(context).textTheme.bodySmall,
                                  ),
                                ),
                                TextButton(
                                  onPressed: loading
                                      ? null
                                      : () => perform(
                                            () => transfer(assignment),
                                          ),
                                  child: const Text('Move between shops'),
                                ),
                              ],
                            ),
                          ),
                        for (final stop in assignment['stops'] as List)
                          Padding(
                            padding: const EdgeInsets.only(top: 12),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  '${stop['customer'] ?? stop['address']} · ${stop['status']}',
                                ),
                                Text('${stop['address_text'] ?? ''}'),
                                if (stop['delivery_note'] != null)
                                  Text(
                                    'Delivery Note: ${stop['delivery_note']}',
                                  ),
                                for (final item in stop['items'] as List? ?? [])
                                  Text(
                                    '${item['product_name']}: ${item['delivered_quantity']} / '
                                    '${item['planned_quantity']} ${item['uom']} delivered',
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
                                    child: const Text('Assign products'),
                                  ),
                                if ((stop['reason'] as String).isNotEmpty)
                                  Text('Reason: ${stop['reason']}'),
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
                                          child: Text(status),
                                        ),
                                    ],
                                  ),
                              ],
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
