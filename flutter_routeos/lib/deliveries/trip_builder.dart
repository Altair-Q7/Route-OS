import 'package:flutter/material.dart';

typedef TripBuilderRequest =
    Future<dynamic> Function(String method, [Map<String, dynamic> data]);

/// One supermarket being planned into a trip before it is sent to the driver.
class DraftStop {
  DraftStop({
    required this.reference,
    required this.customer,
    required this.address,
    required this.latitude,
    required this.longitude,
    this.products = const [],
  });

  final String reference, customer, address;
  final double latitude, longitude;
  List<DraftProduct> products;

  Map<String, dynamic> toJson() => {
    'stop_ref': reference,
    'customer': customer,
    'address': address,
    'latitude': latitude,
    'longitude': longitude,
    'items': [for (final product in products) product.toJson()],
  };
}

class DraftProduct {
  DraftProduct({required this.name, required this.quantity, required this.unit});

  // Mutable so the product rows can be edited in place before saving.
  String name, quantity, unit;

  Map<String, dynamic> toJson() =>
      {'product_name': name, 'planned_quantity': quantity, 'uom': unit};
}

/// Admin screen that builds a delivery trip without needing ERPNext.
///
/// The supervisor's verbal brief is entered here: one row per supermarket with
/// the kg or packet quantities to leave there. Nothing is sent until the admin
/// saves, and each stop must carry at least one product so the driver can
/// confirm a real delivered amount later.
class TripBuilder extends StatefulWidget {
  const TripBuilder({super.key, required this.request});

  final TripBuilderRequest request;

  @override
  State<TripBuilder> createState() => _TripBuilderState();
}

class _TripBuilderState extends State<TripBuilder> {
  final _form = GlobalKey<FormState>();
  final _reference = TextEditingController();
  final _vehicle = TextEditingController();
  final _stops = <DraftStop>[];
  List<Map<String, dynamic>> _drivers = [];
  int? _driverId;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _loadDrivers();
  }

  @override
  void dispose() {
    _reference.dispose();
    _vehicle.dispose();
    super.dispose();
  }

  Future<void> _loadDrivers() async {
    try {
      final result = await widget.request('drivers') as Map;
      if (!mounted) return;
      setState(() => _drivers = (result['drivers'] as List)
          .map((item) => Map<String, dynamic>.from(item as Map))
          .toList());
    } catch (_) {
      if (mounted) setState(() => _drivers = const []);
    }
  }

  bool get _canSave =>
      !_saving &&
      _stops.isNotEmpty &&
      _stops.every((stop) => stop.products.isNotEmpty);

  Future<void> _save() async {
    if (!_form.currentState!.validate() || _driverId == null) return;
    setState(() => _saving = true);
    try {
      await widget.request('delivery.trip.create', {
        'trip': _reference.text.trim(),
        'driver_id': _driverId,
        'vehicle': _vehicle.text.trim(),
        'stops': [for (final stop in _stops) stop.toJson()],
      });
      if (!mounted) return;
      Navigator.pop(context, true);
    } catch (error) {
      if (mounted) {
        setState(() => _saving = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not create the trip: $error')),
        );
      }
    }
  }

  Future<void> _addStop() async {
    final stop = await showDialog<DraftStop>(
      context: context,
      builder: (_) => _StopDialog(stopNumber: _stops.length + 1),
    );
    if (stop != null && mounted) setState(() => _stops.add(stop));
  }

  Future<void> _editStop(int index) async {
    final stop = await showDialog<DraftStop>(
      context: context,
      builder: (_) => _StopDialog(stopNumber: index + 1, initial: _stops[index]),
    );
    if (stop != null && mounted) setState(() => _stops[index] = stop);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Create trip')),
    body: Form(
      key: _form,
      child: Column(
        children: [
          if (_saving) const LinearProgressIndicator(),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(12),
              children: [
                TextFormField(
                  controller: _reference,
                  decoration: const InputDecoration(
                    labelText: 'Trip reference',
                    helperText: 'For example SAP-TRIP-1042. Reusing it never duplicates a trip.',
                  ),
                  validator: (value) => (value ?? '').trim().isEmpty
                      ? 'Enter a trip reference'
                      : null,
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<int>(
                  initialValue: _driverId,
                  decoration: const InputDecoration(labelText: 'Driver'),
                  items: [
                    for (final driver in _drivers)
                      DropdownMenuItem(
                        value: driver['id'] as int,
                        child: Text(driver['name'].toString()),
                      ),
                  ],
                  onChanged: _saving ? null : (value) => setState(() => _driverId = value),
                  validator: (value) => value == null ? 'Choose a driver' : null,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _vehicle,
                  decoration: const InputDecoration(
                    labelText: 'Vehicle number',
                    helperText: 'The driver must start their ride with this exact vehicle.',
                  ),
                  validator: (value) => (value ?? '').trim().isEmpty
                      ? 'Enter the vehicle number'
                      : null,
                ),
                const SizedBox(height: 20),
                Text(
                  'Supermarkets',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                for (var i = 0; i < _stops.length; i++)
                  Card(
                    child: ListTile(
                      title: Text(_stops[i].customer),
                      subtitle: Text(
                        '${_stops[i].products.length} product(s) · '
                        '${_stops[i].products.map((product) => '${product.quantity} ${product.unit}').join(', ')}',
                      ),
                      trailing: IconButton(
                        tooltip: 'Remove stop',
                        icon: const Icon(Icons.delete_outline),
                        onPressed: _saving
                            ? null
                            : () => setState(() => _stops.removeAt(i)),
                      ),
                      onTap: _saving ? null : () => _editStop(i),
                    ),
                  ),
                OutlinedButton.icon(
                  onPressed: _saving ? null : _addStop,
                  icon: const Icon(Icons.add),
                  label: const Text('Add supermarket'),
                ),
                if (_stops.any((stop) => stop.products.isEmpty))
                  const Padding(
                    padding: EdgeInsets.only(top: 12),
                    child: Text(
                      'Every supermarket needs at least one product and quantity, '
                      'otherwise the driver cannot confirm the delivery.',
                    ),
                  ),
              ],
            ),
          ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: FilledButton(
                onPressed: _canSave ? _save : null,
                child: const Text('Create trip'),
              ),
            ),
          ),
        ],
      ),
    ),
  );
}

class _StopDialog extends StatefulWidget {
  const _StopDialog({required this.stopNumber, this.initial});

  final int stopNumber;
  final DraftStop? initial;

  @override
  State<_StopDialog> createState() => _StopDialogState();
}

class _StopDialogState extends State<_StopDialog> {
  final _form = GlobalKey<FormState>();
  late final TextEditingController _reference;
  late final TextEditingController _customer;
  late final TextEditingController _address;
  late final TextEditingController _latitude;
  late final TextEditingController _longitude;
  late List<DraftProduct> _products;

  @override
  void initState() {
    super.initState();
    final initial = widget.initial;
    _reference = TextEditingController(
      text: initial?.reference ?? 'STOP-${widget.stopNumber}',
    );
    _customer = TextEditingController(text: initial?.customer ?? '');
    _address = TextEditingController(text: initial?.address ?? '');
    _latitude = TextEditingController(
      text: initial == null ? '' : initial.latitude.toString(),
    );
    _longitude = TextEditingController(
      text: initial == null ? '' : initial.longitude.toString(),
    );
    _products = [for (final product in initial?.products ?? const <DraftProduct>[]) product];
  }

  @override
  void dispose() {
    _reference.dispose();
    _customer.dispose();
    _address.dispose();
    _latitude.dispose();
    _longitude.dispose();
    super.dispose();
  }

  void _warn(String message) => ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(content: Text(message)),
  );

  void _save() {
    if (!_form.currentState!.validate()) return;
    Navigator.pop(
      context,
      DraftStop(
        reference: _reference.text.trim(),
        customer: _customer.text.trim(),
        address: _address.text.trim(),
        latitude: double.parse(_latitude.text.trim()),
        longitude: double.parse(_longitude.text.trim()),
        products: _products,
      ),
    );
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text('Supermarket ${widget.stopNumber}'),
    scrollable: true,
    content: Form(
      key: _form,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextFormField(
            controller: _customer,
            maxLength: 140,
            decoration: const InputDecoration(labelText: 'Supermarket name'),
            validator: (value) => (value ?? '').trim().isEmpty
                ? 'Enter the supermarket name'
                : null,
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
              'Products to deliver',
              style: Theme.of(context).textTheme.titleSmall,
            ),
          ),
          const SizedBox(height: 8),
          for (var i = 0; i < _products.length; i++)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                children: [
                  Expanded(
                    flex: 3,
                    child: TextFormField(
                      initialValue: _products[i].name,
                      decoration: const InputDecoration(labelText: 'Product'),
                      onChanged: (value) => _products[i].name = value,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextFormField(
                      initialValue: _products[i].quantity,
                      keyboardType: const TextInputType.numberWithOptions(
                        decimal: true,
                      ),
                      decoration: const InputDecoration(labelText: 'Qty'),
                      onChanged: (value) => _products[i].quantity = value,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextFormField(
                      initialValue: _products[i].unit,
                      decoration: const InputDecoration(labelText: 'Unit'),
                      onChanged: (value) => _products[i].unit = value,
                    ),
                  ),
                  IconButton(
                    tooltip: 'Remove product',
                    icon: const Icon(Icons.close),
                    onPressed: () => setState(() => _products.removeAt(i)),
                  ),
                ],
              ),
            ),
          TextButton.icon(
            onPressed: () => setState(
              () => _products.add(
                DraftProduct(name: '', quantity: '', unit: 'kg'),
              ),
            ),
            icon: const Icon(Icons.add),
            label: const Text('Add product'),
          ),
        ],
      ),
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: const Text('Cancel'),
      ),
      FilledButton(
        onPressed: () {
          // A stop without products would leave the driver nothing to confirm,
          // so it is rejected here rather than sent to the server.
          if (_products.isEmpty) {
            _warn('Add at least one product so the driver can confirm the delivery');
            return;
          }
          final validProduct = _products.where(
            (product) =>
                product.name.trim().isNotEmpty &&
                product.unit.trim().isNotEmpty &&
                (double.tryParse(product.quantity.trim()) ?? 0) > 0,
          );
          if (validProduct.length != _products.length) {
            _warn('Each product needs a name, a positive quantity and a unit');
            return;
          }
          _products = [for (final product in validProduct) product];
          _save();
        },
        child: const Text('Save stop'),
      ),
    ],
  );

  String? _coordinate(String? value, {required double limit}) {
    final parsed = double.tryParse((value ?? '').trim());
    if (parsed == null || !parsed.isFinite) return 'Enter a coordinate';
    if (parsed < -limit || parsed > limit) return 'Out of range';
    return null;
  }
}