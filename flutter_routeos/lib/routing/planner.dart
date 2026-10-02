import 'package:flutter/foundation.dart';
import 'dart:math' as math;

enum PlannerState {
  idle,
  drawing,
  calculating,
  ready,
  saving,
  loading,
  navigating,
  error,
}

enum RoutingProfile { car, bicycle, pedestrian }

class RoutePoint {
  final String id, label, address;
  final double latitude, longitude;
  RoutePoint(
    this.latitude,
    this.longitude, {
    String? id,
    this.label = '',
    this.address = '',
  }) : id = id ?? DateTime.now().microsecondsSinceEpoch.toString();
  factory RoutePoint.fromJson(Map<String, dynamic> json) => RoutePoint(
    (json['latitude'] as num).toDouble(),
    (json['longitude'] as num).toDouble(),
    id: json['id']?.toString(),
    label: json['label']?.toString() ?? '',
    address: json['address']?.toString() ?? '',
  );
  Map<String, dynamic> json(int i, int count) => {
    'id': id,
    'sequence': i,
    'latitude': latitude,
    'longitude': longitude,
    'type': i == 0
        ? 'start'
        : i == count - 1
        ? 'destination'
        : 'via',
    'label': label,
    'address': address,
  };
}

class Planner extends ChangeNotifier {
  List<RoutePoint> _points = [];
  final List<List<RoutePoint>> _undo = [], _redo = [];
  List<RoutePoint> get points => List.unmodifiable(_points);
  PlannerState state = PlannerState.idle;
  double distance = 0;
  int duration = 0;
  int? id;
  String name = '';
  RoutingProfile profile = RoutingProfile.car;
  String createdAt = DateTime.now().toUtc().toIso8601String();
  String updatedAt = DateTime.now().toUtc().toIso8601String();
  bool get canUndo => _undo.isNotEmpty;
  bool get canRedo => _redo.isNotEmpty;
  String typeAt(int i) => i == 0
      ? 'Start'
      : i == _points.length - 1
      ? 'Destination'
      : 'Via';
  void edit(List<RoutePoint> next) {
    updatedAt = DateTime.now().toUtc().toIso8601String();
    _undo.add(List.of(_points));
    _redo.clear();
    _points = next;
    id = null;
    distance = 0;
    duration = 0;
    state = _points.isEmpty ? PlannerState.idle : PlannerState.drawing;
    notifyListeners();
  }

  bool add(RoutePoint p) {
    if (_points.length >= 102) return false;
    edit([..._points, p]);
    return true;
  }

  void remove(int i) {
    final next = List.of(_points)..removeAt(i);
    edit(next);
  }

  void move(int i, RoutePoint p) {
    final next = List.of(_points);
    next[i] = RoutePoint(
      p.latitude,
      p.longitude,
      id: next[i].id,
      label: p.label,
      address: p.address,
    );
    edit(next);
  }

  bool insert(int i, RoutePoint p) {
    if (_points.length >= 102) return false;
    final next = List.of(_points)..insert(i, p);
    edit(next);
    return true;
  }

  void reorder(int a, int b) {
    final next = List.of(_points);
    if (b > a) b--;
    next.insert(b, next.removeAt(a));
    edit(next);
  }

  void clear() => edit([]);
  void undo() {
    if (canUndo) {
      _redo.add(List.of(_points));
      _points = _undo.removeLast();
      id = null;
      distance = 0;
      duration = 0;
      state = _points.isEmpty ? PlannerState.idle : PlannerState.drawing;
      notifyListeners();
    }
  }

  void redo() {
    if (canRedo) {
      _undo.add(List.of(_points));
      _points = _redo.removeLast();
      id = null;
      distance = 0;
      duration = 0;
      state = _points.isEmpty ? PlannerState.idle : PlannerState.drawing;
      notifyListeners();
    }
  }

  void calculating() {
    state = _points.length >= 2
        ? PlannerState.calculating
        : PlannerState.drawing;
    notifyListeners();
  }

  void ready(double meters, int seconds) {
    distance = meters;
    duration = seconds;
    state = PlannerState.ready;
    notifyListeners();
  }

  void failed() {
    state = PlannerState.error;
    notifyListeners();
  }

  List<Map<String, dynamic>> encode(List<RoutePoint> points) => [
    for (int i = 0; i < points.length; i++) points[i].json(i, points.length),
  ];
  List<RoutePoint> decode(dynamic points) => (points as List)
      .map((p) => RoutePoint.fromJson(Map<String, dynamic>.from(p as Map)))
      .toList();
  Map<String, dynamic> json() => {
    'id': id,
    'name': name,
    'points': encode(_points),
    'profile': profile.name,
    'distance_meters': distance,
    'duration_seconds': duration,
    'created_at': createdAt,
    'updated_at': updatedAt,
    'undo': _undo.map(encode).toList(),
    'redo': _redo.map(encode).toList(),
  };
  void restore(Map<String, dynamic> data) {
    _points = decode(data['points']);
    name = data['name']?.toString() ?? '';
    id = (data['id'] as num?)?.toInt();
    createdAt = data['created_at']?.toString() ?? createdAt;
    profile = RoutingProfile.values.firstWhere(
      (p) => p.name == data['profile'],
      orElse: () => RoutingProfile.car,
    );
    _undo.clear();
    _redo.clear();
    for (final h in data['undo'] as List? ?? []) {
      _undo.add(decode(h));
    }
    for (final h in data['redo'] as List? ?? []) {
      _redo.add(decode(h));
    }
    state = _points.isEmpty ? PlannerState.idle : PlannerState.drawing;
    notifyListeners();
  }

  /// 2-opt ordering preview with fixed endpoints. Geographic ordering only; OM still computes
  /// every road segment and is the sole authority for driving distance/time.
  List<RoutePoint> optimizedOrder() {
    final next = List.of(_points);
    double cost(RoutePoint a, RoutePoint b) {
      final lat1 = a.latitude * math.pi / 180,
          lat2 = b.latitude * math.pi / 180;
      final dlat = lat2 - lat1,
          dlon = (b.longitude - a.longitude) * math.pi / 180;
      final h =
          math.pow(math.sin(dlat / 2), 2) +
          math.cos(lat1) * math.cos(lat2) * math.pow(math.sin(dlon / 2), 2);
      return 2 * math.asin(math.sqrt(h.clamp(0, 1)));
    }

    bool changed = true;
    int passes = 0;
    while (changed && passes++ < next.length) {
      changed = false;
      for (int i = 1; i < next.length - 2; i++) {
        for (int j = i + 1; j < next.length - 1; j++) {
          if (cost(next[i - 1], next[j]) + cost(next[i], next[j + 1]) + 1e-12 <
              cost(next[i - 1], next[i]) + cost(next[j], next[j + 1])) {
            final segment = next.sublist(i, j + 1).reversed.toList();
            next.replaceRange(i, j + 1, segment);
            changed = true;
          }
        }
      }
    }
    return next;
  }
}
