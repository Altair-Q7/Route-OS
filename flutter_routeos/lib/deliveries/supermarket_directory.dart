import 'package:flutter/material.dart';

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
      title: const Text('Supermarkets'),
      actions: [
        IconButton(
          tooltip: 'Refresh supermarkets',
          onPressed: _loading ? null : _load,
          icon: const Icon(Icons.refresh),
        ),
      ],
    ),
    floatingActionButton: FloatingActionButton.extended(
      onPressed: _loading ? null : () => _edit(),
      icon: const Icon(Icons.add),
      label: const Text('Add supermarket'),
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
                        ? 'No usual allocation yet'
                        : order
                            .map((item) =>
                                '${item['quantity']} ${item['uom']} ${item['product_name']}')
                            .join(', '),
                  ),
                  trailing: shop['active'] == 1
                      ? null
                      : const Chip(label: Text('Inactive')),
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
        }
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
    title: Text(widget.shop == null ? 'Add supermarket' : 'Edit supermarket'),
    scrollable: true,
    content: Form(
      key: _form,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextFormField(
            controller: _name,
            maxLength: 140,
            decoration: const InputDecoration(labelText: 'Supermarket name'),
            validator: (value) =>
                (value ?? '').trim().isEmpty ? 'Enter the name' : null,
          ),
          TextFormField(
            controller: _address,
            maxLength: 500,
            decoration: const InputDecoration(labelText: 'Address'),
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
                  decoration: const InputDecoration(labelText: 'Latitude'),
                  validator: (value) => _coordinate(value, limit: 90),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: TextFormField(
                  controller: _longitude,
                  keyboardType: const TextInputType.numberWithOptions(
                    decimal: true,
                    signed: true,
                  ),
                  decoration: const InputDecoration(labelText: 'Longitude'),
                  validator: (value) => _coordinate(value, limit: 180),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Align(
            alignment: Alignment.centerLeft,
            child: Text(
              'Usual allocation',
              style: Theme.of(context).textTheme.titleSmall,
            ),
          ),
          const SizedBox(height: 4),
          const Text(
            'Applied automatically when a trip includes this shop. Leave empty '
            'if the shop does not take a fixed amount.',
          ),
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
                      label: 'Product',
                      onChanged: (value) => _order[i]['product_name'] = value,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: _OrderField(
                      initial: _order[i]['quantity']!,
                      label: 'Qty',
                      numeric: true,
                      onChanged: (value) => _order[i]['quantity'] = value,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: _OrderField(
                      initial: _order[i]['uom']!,
                      label: 'Unit',
                      onChanged: (value) => _order[i]['uom'] = value,
                    ),
                  ),
                  IconButton(
                    tooltip: 'Remove product',
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
            label: const Text('Add product'),
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
        onPressed: _submit,
        child: const Text('Save'),
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
            content: Text('Each product needs a name, a positive quantity and a unit'),
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
      'latitude': double.parse(_latitude.text.trim().isEmpty ? '0' : _latitude.text.trim()),
      'longitude': double.parse(_longitude.text.trim().isEmpty ? '0' : _longitude.text.trim()),
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
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$error')),
        );
      }
    }
  }

  static String? _coordinate(String? value, {required double limit}) {
    final text = (value ?? '').trim();
    if (text.isEmpty) return null; // a shop may be saved before it is mapped
    final parsed = double.tryParse(text);
    if (parsed == null || !parsed.isFinite) return 'Enter a coordinate';
    if (parsed < -limit || parsed > limit) return 'Out of range';
    return null;
  }
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