import 'package:flutter_test/flutter_test.dart';
import 'package:routeos_shell/routing/planner.dart';

void main() {
  test(
    'native waypoint limit is explicit and does not discard existing points',
    () {
      final planner = Planner();
      for (int i = 0; i < 102; i++) {
        expect(planner.add(RoutePoint(10 + i / 1000, 77, id: '$i')), isTrue);
      }
      expect(planner.add(RoutePoint(12, 77)), isFalse);
      expect(planner.insert(1, RoutePoint(12, 77)), isFalse);
      expect(planner.points.length, 102);
    },
  );
  test(
    'undo invalidates statistics and editing history survives draft restoration',
    () {
      final planner = Planner()
        ..add(RoutePoint(10, 77))
        ..add(RoutePoint(11, 77));
      planner.ready(2000, 400);
      planner.move(1, RoutePoint(11.1, 77));
      planner.ready(2500, 450);
      planner.undo();
      expect(planner.distance, 0);
      expect(planner.state, PlannerState.drawing);
      final restored = Planner()..restore(planner.json());
      expect(restored.canRedo, isTrue);
      restored.redo();
      expect(restored.points.last.latitude, 11.1);
      expect(DateTime.parse(restored.createdAt).isUtc, isTrue);
    },
  );
  test('ordering preview preserves endpoints and the original route', () {
    final planner = Planner();
    for (final longitude in [77.0, 77.03, 77.01, 77.04]) {
      planner.add(RoutePoint(10, longitude));
    }
    final original = planner.json()['points'];
    final preview = planner.optimizedOrder();
    expect(preview.first.id, planner.points.first.id);
    expect(preview.last.id, planner.points.last.id);
    expect(preview[1].longitude, 77.01);
    expect(planner.json()['points'], original);
  });
  test(
    'points gain start, via and destination semantics after edits and reload',
    () {
      final planner = Planner();
      for (int i = 0; i < 20; i++) {
        planner.add(RoutePoint(10 + i / 100, 77));
      }
      final data = planner.json();
      final points = data['points'] as List;
      expect(points.first['type'], 'start');
      expect(points.last['type'], 'destination');
      expect(points[10]['type'], 'via');
      expect(points[10]['sequence'], 10);
      planner.remove(10);
      planner.reorder(1, 5);
      planner.move(3, RoutePoint(12, 78));
      final before = planner.points[3].latitude;
      planner.undo();
      expect(planner.points[3].latitude, isNot(before));
      planner.redo();
      expect(planner.points[3].latitude, before);
      final loaded = Planner()..restore(planner.json());
      expect(loaded.json()['points'], planner.json()['points']);
      planner.clear();
      expect(planner.points, isEmpty);
      planner.undo();
      expect(planner.points.length, 19);
    },
  );
  test(
    'calculation failure is recoverable and route stats come from native result',
    () {
      final planner = Planner()
        ..add(RoutePoint(10, 77))
        ..add(RoutePoint(11, 77));
      planner.calculating();
      expect(planner.state, PlannerState.calculating);
      planner.failed();
      expect(planner.state, PlannerState.error);
      planner.calculating();
      planner.ready(1840, 350);
      expect(planner.state, PlannerState.ready);
      expect(planner.duration, 350);
      planner.add(RoutePoint(12, 77));
      expect(planner.state, PlannerState.drawing);
      expect(planner.distance, 0);
    },
  );
}
