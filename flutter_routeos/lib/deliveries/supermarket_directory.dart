import 'package:flutter/material.dart';
import '../l10n/generated/app_localizations.dart';

typedef DirectoryRequest =
    Future<dynamic> Function(String method, [Map<String, dynamic> data]);

/// Admin view of the supermarkets RouteOS delivers to.
///
/// The usual allocation lives here, so a trip is built by picking shops rather
/// than retyping products and quantities every morning.
class SupermarketDirectory extends StatefulWidget {
  const SupermarketDirectory({super.key, required this.request});

  final DirectoryRequest request;

  @override
  State<SupermarketDirectory> createState() => _SupermarketDirectoryState();
}

class _SupermarketDirectoryState extends State<SupermarketDirectory> {
  List<Map<String, dynamic>> _shops = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final result = await widget.request('supermarkets') as Map;
      if (!mounted) return;
      setState(() {
        _shops = (result['supermarkets'] as List)
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

  Future<void> _edit([Map<String, dynamic>? shop]) async {
    final saved = await showDialog<bool>(
      context: context,
      builder: (_) => _ShopDialog(request: widget.request, shop: shop),
    );
    if (saved == true) await _load();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Text(AppStrings.of(context).shopTitle),
      actions: [
        IconButton(
          tooltip: AppStrings.of(context).shopRefresh,
          onPressed: _loading ? null : _load,
          icon: const Icon(Icons.refresh),
        ),
      ],
    ),
    floatingActionButton: FloatingActionButton.extended(
      onPressed: _loading ? null : () => _edit(),
      icon: const Icon(Icons.add),
      label: Text(AppStrings.of(context).shopAdd),
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
          child: ListView.builder(
            padding: const EdgeInsets.all(12),
            itemCount: _shops.length,
            itemBuilder: (_, i) {
              final shop = _shops[i];
              final order = (shop['standing_order'] as List? ?? [])
                  .map((item) => Map<String, dynamic>.from(item as Map))
                  .toList();
              return Card(
                child: ListTile(
                  title: Text(shop['name'].toString()),
                  subtitle: Text(
                    order.isEmpty
                        ? AppStrings.of(context).shopNoOrder
                        : order
                              .map(
                                (item) =>
                                    '${item['quantity']} ${item['uom']} ${item['product_name']}',
                              )
                              .join(', '),
                  ),
                  trailing: shop['active'] == 1
                      ? null
                      : Chip(label: Text(AppStrings.of(context).shopInactive)),
                  onTap: () => _edit(shop),
                ),
              );
            },
          ),
        ),
      ],
    ),
  );
}

class _ShopDialog extends StatefulWidget {
  const _ShopDialog({required this.request, this.shop});

  final DirectoryRequest request;
  final Map<String, dynamic>? shop;

  @override
  State<_ShopDialog> createState() => _ShopDialogState();
}

class _ShopDialogState extends State<_ShopDialog> {
  final _form = GlobalKey<FormState>();
  late final TextEditingController _name;
  late final TextEditingController _address;
  late final TextEditingController _latitude;
  late final TextEditingController _longitude;
  late List<Map<String, String>> _order;

  @override
  void initState() {
    super.initState();
    final shop = widget.shop;
    _name = TextEditingController(text: shop?['name']?.toString() ?? '');
    _address = TextEditingController(text: shop?['address']?.toString() ?? '');
    _latitude = TextEditingController(
      text: shop == null ? '' : (shop['latitude'] as num).toString(),
    );
    _longitude = TextEditingController(
      text: shop == null ? '' : (shop['longitude'] as num).toString(),
    );
    _order = [
      for (final item in (shop?['standing_order'] as List? ?? []))
        {
          'product_name': item['product_name'].toString(),
          'quantity': item['quantity'].toString(),
          'uom': item['uom'].toString(),
        },
    ];
  }

  @override
  void dispose() {
    _name.dispose();
    _address.dispose();
    _latitude.dispose();
    _longitude.dispose();
    super.dispose();
  }

  Future<dynamic> _send(String method, Map<String, dynamic> data) =>
      widget.request(method, data);

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text(
      widget.shop == null
          ? AppStrings.of(context).shopAdd
          : AppStrings.of(context).shopEdit,
    ),
    scrollable: true,
    content: Form(
      key: _form,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextFormField(
            controller: _name,
            maxLength: 140,
            decoration: InputDecoration(
              labelText: AppStrings.of(context).shopName,
            ),
            validator: (value) => (value ?? '').trim().isEmpty
                ? AppStrings.of(context).shopNameRequired
                : null,
          ),
          TextFormField(
            controller: _address,
            maxLength: 500,
            decoration: InputDecoration(
              labelText: AppStrings.of(context).tripBuilderAddress,
            ),
          ),
          Row(
            children: [
              Expanded(
                child: TextFormField(
                  controller: _latitude,
                  keyboardType: const TextInputType.numberWithOptions(
                    decimal: true,
                    signed: true,
                  ),
                  decoration: InputDecoration(
                    labelText: AppStrings.of(context).tripBuilderLatitude,
                  ),
                  validator: (value) => validateCoordinate(
                    value,
                    limit: 90,
                    missing: AppStrings.of(
                      context,
                    ).tripBuilderCoordinateMissing,
                    outOfRange: AppStrings.of(
                      context,
                    ).tripBuilderCoordinateRange,
                  ),
                ),
              ),
              SizedBox(width: 12),
              Expanded(
                child: TextFormField(
                  controller: _longitude,
                  keyboardType: const TextInputType.numberWithOptions(
                    decimal: true,
                    signed: true,
                  ),
                  decoration: InputDecoration(
                    labelText: AppStrings.of(context).tripBuilderLongitude,
                  ),
                  validator: (value) => validateCoordinate(
                    value,
                    limit: 180,
                    missing: AppStrings.of(
                      context,
                    ).tripBuilderCoordinateMissing,
                    outOfRange: AppStrings.of(
                      context,
                    ).tripBuilderCoordinateRange,
                  ),
                ),
              ),
            ],
          ),
          SizedBox(height: 12),
          Align(
            alignment: Alignment.centerLeft,
            child: Text(
              AppStrings.of(context).shopUsualOrder,
              style: Theme.of(context).textTheme.titleSmall,
            ),
          ),
          SizedBox(height: 4),
          Text(AppStrings.of(context).shopUsualOrderHint),
          const SizedBox(height: 8),
          for (var i = 0; i < _order.length; i++)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                children: [
                  Expanded(
                    flex: 3,
                    child: _OrderField(
                      initial: _order[i]['product_name']!,
                      label: AppStrings.of(context).tripBuilderProduct,
                      onChanged: (value) => _order[i]['product_name'] = value,
                    ),
                  ),
                  SizedBox(width: 8),
                  Expanded(
                    child: _OrderField(
                      initial: _order[i]['quantity']!,
                      label: AppStrings.of(context).tripBuilderQuantity,
                      numeric: true,
                      onChanged: (value) => _order[i]['quantity'] = value,
                    ),
                  ),
                  SizedBox(width: 8),
                  Expanded(
                    child: _OrderField(
                      initial: _order[i]['uom']!,
                      label: AppStrings.of(context).tripBuilderUnit,
                      onChanged: (value) => _order[i]['uom'] = value,
                    ),
                  ),
                  IconButton(
                    tooltip: AppStrings.of(context).tripBuilderRemoveProduct,
                    icon: const Icon(Icons.close),
                    onPressed: () => setState(() => _order.removeAt(i)),
                  ),
                ],
              ),
            ),
          TextButton.icon(
            onPressed: () => setState(
              () => _order.add({
                'product_name': '',
                'quantity': '',
                'uom': 'packet',
              }),
            ),
            icon: const Icon(Icons.add),
            label: Text(AppStrings.of(context).tripBuilderAddProduct),
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
        onPressed: _submit,
        child: Text(AppStrings.of(context).actionSave),
      ),
    ],
  );

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    final items = <Map<String, String>>[];
    for (final line in _order) {
      final quantity = double.tryParse(line['quantity']!.trim());
      if (line['product_name']!.trim().isEmpty ||
          line['uom']!.trim().isEmpty ||
          quantity == null ||
          quantity <= 0) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Each product needs a name, a positive quantity and a unit',
            ),
          ),
        );
        return;
      }
      items.add({
        'product_name': line['product_name']!.trim(),
        'uom': line['uom']!.trim(),
        'planned_quantity': line['quantity']!.trim(),
      });
    }
    final body = {
      'name': _name.text.trim(),
      'address': _address.text.trim(),
      'latitude': double.parse(
        _latitude.text.trim().isEmpty ? '0' : _latitude.text.trim(),
      ),
      'longitude': double.parse(
        _longitude.text.trim().isEmpty ? '0' : _longitude.text.trim(),
      ),
      'standing_order': items,
    };
    try {
      if (widget.shop == null) {
        await _send('supermarket.create', body);
      } else {
        await _send('supermarket.update', {...body, 'id': widget.shop!['id']});
      }
      if (mounted) Navigator.pop(context, true);
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('$error')));
      }
    }
  }
}

/// A shop may be saved before it has coordinates, so an empty value is allowed.
String? validateCoordinate(
  String? value, {
  required double limit,
  required String missing,
  required String outOfRange,
}) {
  final text = (value ?? '').trim();
  if (text.isEmpty) return null;
  final parsed = double.tryParse(text);
  if (parsed == null || !parsed.isFinite) return missing;
  if (parsed < -limit || parsed > limit) return outOfRange;
  return null;
}

class _OrderField extends StatelessWidget {
  const _OrderField({
    required this.initial,
    required this.label,
    required this.onChanged,
    this.numeric = false,
  });

  final String initial, label;
  final ValueChanged<String> onChanged;
  final bool numeric;

  @override
  Widget build(BuildContext context) => TextFormField(
    initialValue: initial,
    keyboardType: numeric
        ? const TextInputType.numberWithOptions(decimal: true)
        : TextInputType.text,
    decoration: InputDecoration(labelText: label),
    onChanged: onChanged,
  );
}
