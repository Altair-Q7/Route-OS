import 'package:flutter/material.dart';

import '../l10n/generated/app_localizations.dart';

typedef ReportRequest =
    Future<dynamic> Function(String method, [Map<String, dynamic> data]);

/// Admin view of confirmed delivery results.
///
/// This renders the same projection the customer's API serves, so what the admin
/// sees here is exactly what their system will read.
class DeliveryReports extends StatefulWidget {
  const DeliveryReports({super.key, required this.request});

  final ReportRequest request;

  @override
  State<DeliveryReports> createState() => _DeliveryReportsState();
}

class _DeliveryReportsState extends State<DeliveryReports> {
  List<Map<String, dynamic>> _trips = [];
  List<Map<String, dynamic>> _totals = [];
  List<Map<String, dynamic>> _shortages = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final result = await widget.request('reports.deliveries') as Map;
      if (!mounted) return;
      setState(() {
        _trips = (result['trips'] as List)
            .map((item) => Map<String, dynamic>.from(item as Map))
            .toList();
        _totals = (result['product_totals'] as List)
            .map((item) => Map<String, dynamic>.from(item as Map))
            .toList();
        _shortages = (result['shortages'] as List)
            .map((item) => Map<String, dynamic>.from(item as Map))
            .toList();
        _error = null;
      });
    } catch (error) {
      if (mounted) setState(() => _error = '$error');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppStrings.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(t.reportsTitle),
        actions: [
          IconButton(
            tooltip: t.actionRefresh,
            onPressed: _loading ? null : _load,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: Column(
        children: [
          if (_loading) const LinearProgressIndicator(),
          if (_error != null)
            ListTile(
              leading: const Icon(Icons.error_outline),
              title: Text(_error!),
              trailing: IconButton(
                icon: const Icon(Icons.refresh),
                onPressed: _load,
              ),
            ),
          Expanded(
            child: _loading && _trips.isEmpty
                ? const SizedBox.shrink()
                : ListView(
                    padding: const EdgeInsets.all(12),
                    children: [
                      if (_shortages.isNotEmpty) ...[
                        Text(
                          t.reportsShortages,
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 4),
                        for (final shortage in _shortages)
                          Card(
                            color: const Color(0x33202840),
                            child: ListTile(
                              title: Text(
                                '${shortage['customer']} · ${shortage['trip']}',
                              ),
                              subtitle: Text(
                                '${(shortage['items'] as List).map((item) => '${item['delivered_quantity']}/${item['planned_quantity']} ${item['uom']} ${item['product_name']}').join(', ')}'
                                '${(shortage['reason'] as String? ?? '').isEmpty ? '' : '\n${shortage['reason']}'}',
                              ),
                            ),
                          ),
                        const SizedBox(height: 16),
                      ],
                      if (_totals.isNotEmpty) ...[
                        Text(
                          t.reportsTotals,
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 4),
                        Card(
                          child: Column(
                            children: [
                              for (final total in _totals)
                                ListTile(
                                  dense: true,
                                  title: Text(
                                    '${total['product_name']} (${total['uom']})',
                                  ),
                                  trailing: Text(
                                    '${total['delivered_quantity']} / ${total['planned_quantity']}',
                                  ),
                                ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 16),
                      ],
                      Text(
                        t.reportsTrips,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 4),
                      if (_trips.isEmpty)
                        Padding(
                          padding: const EdgeInsets.all(16),
                          child: Text(t.reportsEmpty),
                        ),
                      for (final trip in _trips)
                        Card(
                          child: ExpansionTile(
                            title: Text(trip['trip'].toString()),
                            subtitle: Text(
                              '${trip['driver_name']} · ${trip['status']}',
                            ),
                            children: [
                              for (final stop in trip['stops'] as List)
                                ListTile(
                                  dense: true,
                                  title: Text(
                                    '${stop['customer']} · ${stop['status']}',
                                  ),
                                  subtitle: Text(
                                    (stop['items'] as List)
                                        .map(
                                          (item) =>
                                              '${item['delivered_quantity']}/${item['planned_quantity']} ${item['uom']} ${item['product_name']}',
                                        )
                                        .join(', '),
                                  ),
                                ),
                            ],
                          ),
                        ),
                    ],
                  ),
          ),
        ],
      ),
    );
  }
}
