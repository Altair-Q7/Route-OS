import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../core/bridge.dart';
import '../map/native_map.dart';
import '../routing/planner.dart';

class RouteOsFlutterHome extends StatefulWidget {
  const RouteOsFlutterHome({super.key});
  @override
  State<RouteOsFlutterHome> createState() => _HomeState();
}

class _HomeState extends State<RouteOsFlutterHome> with WidgetsBindingObserver {
  final planner = Planner();
  StreamSubscription<dynamic>? subscription;
  Map<String, dynamic> session = {};
  List<Map<String, dynamic>> routes = [];
  List<Map<String, dynamic>> searchResults = [];
  bool searching = false;
  String page = 'home', filter = '', query = '';
  String? error;
  Map<String, dynamic>? navigation;
  final navigationStatus = ValueNotifier<Map<String, dynamic>?>(null);
  Map<String, dynamic> tracking = {};
  bool recording = false;
  Map<String, dynamic> recordingStats = {};
  StateSetter? searchUpdate;
  Timer? adminTimer;
  bool adminLoading = false, foreground = true;
  List<Map<String, dynamic>> activeRides = [];
  bool busy = false;
  bool rideStarting = false;
  bool authRequired = false;
  int? moving, inserting;
  Timer? calculationTimeout;
  Completer<bool>? calculationWaiter;
  int calculationGeneration = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    subscription = Bridge.events
        .receiveBroadcastStream({'version': 1})
        .listen(event, onError: (Object e) => message(e.toString()));
    planner.addListener(() {
      if (mounted) setState(() {});
    });
    restore();
  }

  Future<void> restore() async {
    try {
      final value = await Bridge.call('session');
      if (!mounted) return;
      setState(() => session = Map<String, dynamic>.from(value as Map));
      recording = session['recording'] == true;
      if ((session['active_ride_id'] as num? ?? 0) > 0) {
        navigation = {'maneuver': 'Ride active — waiting for GPS'};
        notifyNavigation();
      }
      final draft = await Bridge.call('draft.load');
      if (!mounted) return;
      if (session['role'] != 'admin' && draft is Map && draft['points'] is List) {
        planner.restore(Map<String, dynamic>.from(draft));
        if (['home', 'routes', 'planner'].contains(draft['ui_page'])) {
          page = draft['ui_page'] as String;
        }
      }
      if ((session['id'] as num? ?? 0) > 0) {
        await refresh();
        if (!mounted) return;
        if (session['role'] == 'driver') {
          final ride = await request('ride.restore');
          if (!mounted) return;
          setState(() {
            if (ride == null) {
              navigation = null;
              session.remove('active_ride_id');
            } else {
              session['active_ride_id'] = ride['id'];
              navigation ??= {'maneuver': 'Ride active — waiting for GPS'};
            }
          });
          notifyNavigation();
        }
        if (navigation == null) await request('preview.clear');
        if (navigation == null &&
            !recording &&
            page == 'planner' &&
            planner.points.isNotEmpty) {
          await calculate();
        }
      }
    } catch (e) {
      if (!mounted) return;
      if (e is PlatformException && e.code == 'AUTH_EXPIRED') {
        setState(() => authRequired = true);
      }
      message('Could not restore your session: $e');
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    subscription?.cancel();
    cancelCalculation();
    adminTimer?.cancel();
    navigationStatus.dispose();
    planner.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    foreground = state == AppLifecycleState.resumed;
    if (!foreground) adminTimer?.cancel();
    if (state == AppLifecycleState.resumed && session.isNotEmpty) refresh();
  }

  void message(String text) {
    if (!mounted) return;
    setState(() => error = text);
  }

  void notifyNavigation() {
    navigationStatus.value = navigation == null
        ? null
        : {
            ...navigation!,
            'tracking_message': tracking['message'],
            'tracking_state': tracking['state'],
          };
  }

  Future<dynamic> request(
    String method, [
    Map<String, dynamic> data = const {},
  ]) async {
    try {
      final value = await Bridge.call(method, data);
      if (!mounted) throw StateError('Screen closed');
      return value;
    } catch (e) {
      if (mounted && e is PlatformException && e.code == 'AUTH_EXPIRED') {
        setState(() => authRequired = true);
      }
      message(e is PlatformException ? e.message ?? e.code : e.toString());
      rethrow;
    }
  }

  Future<void> command(
    String method, [
    Map<String, dynamic> data = const {},
  ]) async {
    if (!mounted) return;
    try {
      await request(method, data);
    } catch (_) {}
  }

  Future<void> refresh() async {
    final account = session['id'];
    try {
      final value = await request('routes');
      if (mounted && account == session['id']) {
        setState(
          () => routes = (value as List)
              .map((e) => Map<String, dynamic>.from(e as Map))
              .toList(),
        );
      }
    } catch (_) {}
    if (mounted &&
        session['role'] == 'admin' &&
        !adminLoading &&
        !authRequired) {
      pollAdmin();
    }
  }

  Future<void> pollAdmin() async {
    adminTimer?.cancel();
    if (!mounted || !foreground || session['role'] != 'admin' || adminLoading) {
      return;
    }
    adminLoading = true;
    final account = session['id'];
    try {
      final rides = (await request('active') as List)
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();
      if (mounted &&
          foreground &&
          account == session['id'] &&
          session['role'] == 'admin') {
        setState(() => activeRides = rides);
        await request('admin.points', {'rides': rides});
      }
    } catch (_) {
    } finally {
      adminLoading = false;
      if (mounted &&
          foreground &&
          session['role'] == 'admin' &&
          !authRequired) {
        adminTimer = Timer(const Duration(seconds: 5), pollAdmin);
      }
    }
  }

  void event(dynamic raw) {
    if (!mounted || raw is! Map || raw['version'] != 1) return;
    final data = raw['data'];
    switch (raw['type']) {
      case 'map.tap':
        if (page != 'planner' || navigation != null || rideStarting || busy) {
          return;
        }
        final point = RoutePoint.fromJson(
          Map<String, dynamic>.from(data as Map),
        );
        if (moving != null) {
          planner.move(moving!, point);
          moving = null;
        } else if (inserting != null) {
          if (!planner.insert(inserting! + 1, point)) {
            message('Maximum 102 route points reached.');
          }
          inserting = null;
        } else {
          if (!planner.add(point)) message('Maximum 102 route points reached.');
        }
        calculate();
      case 'map.point.selected':
        if (page == 'planner' &&
            navigation == null &&
            planner.points.isNotEmpty) {
          final index = (data['index'] as num).toInt();
          pointActions(index < 0 ? planner.points.length - 1 : index);
        }
      case 'route.ready':
        if (data['generation'] != calculationGeneration ||
            planner.state != PlannerState.calculating) {
          return;
        }
        calculationTimeout?.cancel();
        if (!(calculationWaiter?.isCompleted ?? true)) {
          calculationWaiter!.complete(true);
        }
        planner.ready(
          (data['distance_meters'] as num).toDouble(),
          (data['duration_seconds'] as num).toInt(),
        );
      case 'route.failed':
        if (data['generation'] != calculationGeneration) {
          if (navigation != null || rideStarting) {
            message(data['message'].toString());
          }
          return;
        }
        calculationTimeout?.cancel();
        if (!(calculationWaiter?.isCompleted ?? true)) {
          calculationWaiter!.complete(false);
        }
        planner.failed();
        message(data['message'].toString());
      case 'search.results':
        setState(
          () => searchResults = (data as List)
              .map((e) => Map<String, dynamic>.from(e as Map))
              .toList(),
        );
        searchUpdate?.call(() {});
      case 'search.finished':
        searching = false;
        searchUpdate?.call(() {});
      case 'navigation.started':
        planner.state = PlannerState.navigating;
        setState(() {
          page = 'home';
          navigation = {
            'maneuver': 'Waiting for GPS guidance',
            ...Map<String, dynamic>.from(data as Map),
          };
        });
        notifyNavigation();
      case 'navigation.arrived':
        navigation = {...?navigation, 'arrived': true};
        notifyNavigation();
      case 'navigation.progress':
        navigation = Map<String, dynamic>.from(data as Map);
        notifyNavigation();
      case 'tracking.status':
        tracking = Map<String, dynamic>.from(data as Map);
        if (tracking['state'] == 'auth_required') {
          setState(() => authRequired = true);
        }
        notifyNavigation();
      case 'navigation.stopped':
        planner.state = PlannerState.drawing;
        setState(() {
          navigation = null;
          tracking = {};
          session.remove('active_ride_id');
          page = 'home';
        });
        navigationStatus.value = null;
      case 'recording.started':
        setState(() => recording = true);
      case 'recording.stopped':
        setState(() => recording = false);
        refresh();
      case 'recording.progress':
        setState(() => recordingStats = Map<String, dynamic>.from(data as Map));
    }
  }

  void cancelCalculation() {
    calculationGeneration++;
    calculationTimeout?.cancel();
    if (!(calculationWaiter?.isCompleted ?? true)) {
      calculationWaiter!.complete(false);
    }
    calculationWaiter = null;
  }

  Future<void> calculate({Completer<bool>? waiter}) async {
    if (rideStarting || !mounted) {
      waiter?.complete(false);
      return;
    }
    cancelCalculation();
    final generation = calculationGeneration;
    calculationWaiter = waiter;
    if (planner.points.length > 102) {
      message(
        'Organic Maps supports 100 waypoints plus start and destination.',
      );
      waiter?.complete(false);
      return;
    }
    planner.calculating();
    final definition = planner.json();
    try {
      await request('draft.save', {...definition, 'ui_page': page});
      if (!mounted || generation != calculationGeneration) return;
      await request('calculate', {
        'points': definition['points'],
        'profile': definition['profile'],
        'generation': generation,
      });
      if (!mounted || generation != calculationGeneration) return;
      if (planner.state == PlannerState.calculating) {
        calculationTimeout = Timer(const Duration(seconds: 60), () {
          if (!mounted || generation != calculationGeneration) return;
          planner.failed();
          if (!(calculationWaiter?.isCompleted ?? true)) {
            calculationWaiter!.complete(false);
          }
          message(
            'Route calculation timed out. Check regional maps and retry.',
          );
        });
      }
    } catch (_) {
      if (!mounted || generation != calculationGeneration) return;
      planner.failed();
      if (!(calculationWaiter?.isCompleted ?? true)) {
        calculationWaiter!.complete(false);
      }
    }
  }

  Future<bool> calculateAndWait() async {
    if (planner.points.length < 2) {
      await calculate();
      return false;
    }
    final waiter = Completer<bool>();
    await calculate(waiter: waiter);
    try {
      return await waiter.future.timeout(const Duration(seconds: 65));
    } on TimeoutException {
      if (!waiter.isCompleted) waiter.complete(false);
      return false;
    } finally {
      if (identical(calculationWaiter, waiter)) calculationWaiter = null;
    }
  }

  Future<void> locate({bool add = false}) async {
    if (add && (busy || rideStarting || navigation != null)) return;
    try {
      final p = await request('location');
      if (add) {
        if (!planner.add(
          RoutePoint.fromJson(Map<String, dynamic>.from(p as Map)),
        )) {
          message('Maximum 100 waypoints plus start and destination.');
          return;
        }
        await calculate();
      }
    } catch (_) {}
  }

  Future<void> load(Map<String, dynamic> route) async {
    setState(() => busy = true);
    planner.state = PlannerState.loading;
    try {
      final value = Map<String, dynamic>.from(
        await request('route', {'id': route['id']}) as Map,
      );
      if (!mounted) return;
      planner.restore(value);
      if ((value['recorded_track_point_count'] as num? ?? 0) >
          planner.points.length) {
        message(
          'Original GPS track preserved. Navigation uses ${planner.points.length} native routing anchors from ${value['recorded_track_point_count']} recorded fixes.',
        );
      }
      setState(() => page = 'planner');
      if (!await calculateAndWait()) {
        message(
          'Could not calculate this route. Check offline map coverage and retry.',
        );
      }
    } catch (_) {
      message('Could not load this route. Check your connection and retry.');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<String?> nameDialog(String title, [String initial = '']) async {
    if (!mounted) return null;
    final input = TextEditingController(text: initial);
    final value = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
        content: TextField(
          controller: input,
          autofocus: true,
          maxLength: 160,
          decoration: const InputDecoration(labelText: 'Route name'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              if (input.text.trim().isNotEmpty) {
                Navigator.pop(ctx, input.text.trim());
              }
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
    return value;
  }

  Future<bool> confirm(String title, String description) async =>
      await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text(title),
          content: Text(description),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('Confirm'),
            ),
          ],
        ),
      ) ??
      false;
  Future<void> save() async {
    if (planner.state != PlannerState.ready) return;
    final name = await nameDialog('Save route', planner.name);
    if (!mounted || name == null) return;
    setState(() => busy = true);
    planner.state = PlannerState.saving;
    try {
      final route = await request('save', {
        'name': name,
        'points': planner.json()['points'],
        'profile': planner.profile.name,
        'distance_meters': planner.distance,
        'duration_seconds': planner.duration,
      });
      planner.id = (route['id'] as num).toInt();
      planner.name = name;
      await refresh();
      message('Route saved and available to other drivers.');
    } catch (_) {
    } finally {
      if (mounted) {
        planner.state = PlannerState.ready;
        setState(() => busy = false);
        await command('draft.save', {...planner.json(), 'ui_page': page});
      }
    }
  }

  Future<void> vehicle() async {
    if (planner.state != PlannerState.ready) return;
    if (planner.id == null) {
      await save();
      if (planner.id == null) return;
    }
    if (!mounted) return;
    final number = TextEditingController();
    String type = 'car';
    final selected = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, set) => AlertDialog(
          title: const Text('Select vehicle'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DropdownButtonFormField<String>(
                initialValue: type,
                items: ['car', 'bike', 'van', 'truck']
                    .map(
                      (v) => DropdownMenuItem(
                        value: v,
                        child: Text(v.toUpperCase()),
                      ),
                    )
                    .toList(),
                onChanged: (v) => set(() => type = v!),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: number,
                decoration: const InputDecoration(labelText: 'Vehicle number'),
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
                if (number.text.trim().isNotEmpty) Navigator.pop(ctx, true);
              },
              child: const Text('Start ride'),
            ),
          ],
        ),
      ),
    );
    if (!mounted || selected != true) return;
    setState(() {
      busy = true;
      rideStarting = true;
    });
    try {
      await request('ride.start', {
        'id': planner.id,
        'vehicle_type': type,
        'vehicle_number': number.text.trim(),
      });
    } catch (_) {
      if (mounted) planner.failed();
    } finally {
      if (mounted) {
        setState(() {
          busy = false;
          rideStarting = false;
        });
      }
    }
  }

  Future<void> startSavedRoute(Map<String, dynamic> route) async {
    if (route['route_type'] == 'recorded') {
      planner.restore({'points': []});
      planner.id = (route['id'] as num).toInt();
      planner.name = route['name']?.toString() ?? '';
      planner.distance = (route['distance_meters'] as num? ?? 0).toDouble();
      planner.duration = (route['duration_seconds'] as num? ?? 0).toInt();
      planner.state = PlannerState.ready;
      if (mounted) setState(() {});
      await vehicle();
      return;
    }
    await load(route);
    if (!mounted || planner.state != PlannerState.ready) return;
    await vehicle();
  }

  Future<void> endRide() async {
    if (!await confirm(
      'End this ride?',
      'Live tracking stops after RouteOS confirms the ride has ended.',
    )) {
      return;
    }
    if (!mounted) return;
    try {
      await request('ride.end');
      setState(() {
        navigation = null;
        page = 'home';
      });
      navigationStatus.value = null;
      await command('draft.save', {...planner.json(), 'ui_page': page});
      await refresh();
    } catch (_) {}
  }

  Future<void> changePage(String next) async {
    if (!mounted || busy) return;
    if (next == 'planner' && session['role'] == 'admin') {
      message('Route drawing is available to drivers only.');
      return;
    }
    if (rideStarting) {
      message('Starting navigation — please wait.');
      return;
    }
    if (navigation != null) {
      await endRide();
      return;
    }
    if (recording) {
      message('Stop or discard the recording first.');
      return;
    }
    setState(() => page = next);
    await command('draft.save', {...planner.json(), 'ui_page': page});
    if (!mounted) return;
    if (next == 'home') {
      cancelCalculation();
      await command('preview.clear');
    }
    if (next == 'routes') await refresh();
    if (next == 'planner' && planner.points.isNotEmpty) await calculate();
  }

  Future<void> pointActions(int index) async {
    if (rideStarting || busy) return;
    if (index < 0 || index >= planner.points.length) return;
    final p = planner.points[index];
    final action = await showModalBottomSheet<String>(
      context: context,
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              title: Text('Point ${index + 1} · ${planner.typeAt(index)}'),
              subtitle: Text(
                '${p.label}\n${p.latitude.toStringAsFixed(5)}, ${p.longitude.toStringAsFixed(5)}',
              ),
            ),
            for (final item in ['Move on map', 'Insert after', 'Delete point'])
              ListTile(
                title: Text(item),
                onTap: () => Navigator.pop(ctx, item),
              ),
          ],
        ),
      ),
    );
    if (!mounted) return;
    if (action == 'Delete point') {
      planner.remove(index);
      await calculate();
    }
    if (action == 'Move on map') setState(() => moving = index);
    if (action == 'Insert after') setState(() => inserting = index);
  }

  Future<void> login([String? selected]) async {
    if (!mounted) return;
    final name = TextEditingController(
      text:
          selected ?? (authRequired ? session['name']?.toString() : null) ?? '',
    );
    final password = TextEditingController();
    final submitted = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Sign in to RouteOS'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: name,
              decoration: const InputDecoration(labelText: 'Account name'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: password,
              obscureText: true,
              decoration: const InputDecoration(labelText: 'Password'),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Sign in'),
          ),
        ],
      ),
    );
    if (!mounted || submitted != true) return;
    try {
      final user = await request('login', {
        'name': name.text.trim(),
        'password': password.text.isEmpty ? null : password.text,
      });
      if (!mounted) return;
      setState(() {
        authRequired = false;
        session = {...session, ...Map<String, dynamic>.from(user as Map)};
      });
      await restore();
    } catch (_) {}
  }

  Future<void> server() async {
    final value = await nameDialog('RouteOS server HTTPS URL');
    if (value != null) {
      try {
        await request('server', {'url': value});
        if (!mounted) return;
        cancelCalculation();
        planner.restore({'points': []});
        setState(() {
          session = {'development': session['development']};
          routes = [];
          activeRides = [];
          page = 'home';
          authRequired = false;
        });
        await restore();
        message('Server configured.');
      } catch (_) {}
    }
  }

  Future<void> optimize() async {
    if (busy || rideStarting || navigation != null) return;
    final order = planner.optimizedOrder();
    final positions = order
        .map((p) => planner.points.indexWhere((old) => old.id == p.id) + 1)
        .join(' → ');
    if (await confirm(
          'Optimize waypoint order?',
          'Proposed order: $positions\nStart and destination stay fixed. This shortens geographic waypoint order, not necessarily road travel time. Organic Maps recalculates the road route. Undo restores the original order.',
        ) &&
        mounted) {
      planner.edit(order);
      await calculate();
    }
  }

  void pointsSheet() {
    if (busy || rideStarting || navigation != null) return;
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, update) => SizedBox(
          height: MediaQuery.sizeOf(ctx).height * .65,
          child: Column(
            children: [
              const Padding(
                padding: EdgeInsets.all(18),
                child: Text(
                  'Route points',
                  style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                ),
              ),
              Expanded(
                child: ReorderableListView.builder(
                  itemCount: planner.points.length,
                  onReorderItem: (a, b) {
                    planner.reorder(a, b > a ? b + 1 : b);
                    update(() {});
                    calculate();
                  },
                  itemBuilder: (ctx, i) {
                    final p = planner.points[i];
                    return ListTile(
                      key: ValueKey(p.id),
                      leading: CircleAvatar(child: Text('${i + 1}')),
                      title: Text(
                        p.label.isEmpty ? planner.typeAt(i) : p.label,
                      ),
                      subtitle: Text(
                        '${p.latitude.toStringAsFixed(5)}, ${p.longitude.toStringAsFixed(5)}',
                      ),
                      trailing: PopupMenuButton<String>(
                        tooltip: 'Edit point ${i + 1}',
                        onSelected: (action) {
                          if (action == 'delete') {
                            planner.remove(i);
                            update(() {});
                            calculate();
                          }
                          if (action == 'up' || action == 'down') {
                            planner.reorder(i, action == 'up' ? i - 1 : i + 2);
                            update(() {});
                            calculate();
                          }
                          if (action == 'move' || action == 'insert') {
                            setState(() {
                              if (action == 'move') {
                                moving = i;
                              } else {
                                inserting = i;
                              }
                            });
                            Navigator.pop(ctx);
                          }
                        },
                        itemBuilder: (_) => [
                          if (i > 0)
                            const PopupMenuItem(
                              value: 'up',
                              child: Text('Move earlier'),
                            ),
                          if (i < planner.points.length - 1)
                            const PopupMenuItem(
                              value: 'down',
                              child: Text('Move later'),
                            ),
                          const PopupMenuItem(
                            value: 'move',
                            child: Text('Move on map'),
                          ),
                          const PopupMenuItem(
                            value: 'insert',
                            child: Text('Insert after'),
                          ),
                          const PopupMenuItem(
                            value: 'delete',
                            child: Text('Delete'),
                          ),
                        ],
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> searchSheet() async {
    final input = TextEditingController();
    searchResults = [];
    searching = false;
    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, update) {
          searchUpdate = update;
          return SizedBox(
            height: MediaQuery.sizeOf(ctx).height * .7,
            child: Column(
              children: [
                Padding(
                  padding: const EdgeInsets.all(16),
                  child: TextField(
                    controller: input,
                    decoration: InputDecoration(
                      labelText: 'Search destination',
                      prefixIcon: Icon(Icons.search),
                      suffixIcon: IconButton(
                        tooltip: 'Clear search',
                        icon: const Icon(Icons.close),
                        onPressed: () {
                          input.clear();
                          update(() {
                            searchResults = [];
                            searching = false;
                          });
                          command('search', {'query': ''});
                        },
                      ),
                    ),
                    onSubmitted: (text) async {
                      update(() {
                        searching = true;
                        searchResults = [];
                      });
                      try {
                        await request('search', {'query': text});
                      } catch (_) {
                        searching = false;
                        searchUpdate?.call(() {});
                      }
                    },
                  ),
                ),
                if (searching) const LinearProgressIndicator(),
                if (!searching && searchResults.isEmpty)
                  const Padding(
                    padding: EdgeInsets.all(16),
                    child: Text(
                      'Search offline places and addresses. Download the regional map for local results.',
                    ),
                  ),
                Expanded(
                  child: ListView.builder(
                    itemCount: searchResults.length,
                    itemBuilder: (_, i) {
                      final p = searchResults[i];
                      return ListTile(
                        title: Text(p['label'].toString()),
                        subtitle: Text(p['address'].toString()),
                        onTap: () {
                          if (session['role'] == 'admin') {
                            command('center', p);
                            Navigator.pop(ctx);
                            return;
                          }
                          if (navigation != null || busy || rideStarting) {
                            message('End navigation before editing a route.');
                            return;
                          }
                          if (!planner.add(RoutePoint.fromJson(p))) {
                            message(
                              'Maximum 100 waypoints plus start and destination.',
                            );
                            return;
                          }
                          command('center', p);
                          Navigator.pop(ctx);
                          setState(() => page = 'planner');
                          calculate();
                        },
                      );
                    },
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
    searchUpdate = null;
    input.dispose();
  }

  Future<void> routeActions(Map<String, dynamic> route) async {
    await showModalBottomSheet(
      context: context,
      builder: (ctx) => SafeArea(
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                title: Text(
                  route['name'].toString(),
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                subtitle: Text(
                  '${route['route_type']} · ${km(route['distance_meters'])} · ${minutes(route['duration_seconds'])}',
                ),
              ),
              if (session['role'] != 'admin')
                ListTile(
                  leading: const Icon(Icons.play_arrow),
                  title: const Text('Start ride'),
                  subtitle: const Text(
                    'Load route, choose a vehicle, and start navigation',
                  ),
                  onTap: () {
                    Navigator.pop(ctx);
                    startSavedRoute(route);
                  },
                ),
              if (session['role'] != 'admin' && route['route_type'] == 'drawn')
                ListTile(
                  leading: const Icon(Icons.map_outlined),
                  title: const Text('Open / edit drawn route'),
                  onTap: () {
                    Navigator.pop(ctx);
                    load(route);
                  },
                )
              else
                const ListTile(
                  leading: Icon(Icons.fiber_manual_record),
                  title: Text('Recorded track'),
                  subtitle: Text(
                    'Original GPS track is kept separate from drawn routes.',
                  ),
                ),
              ListTile(
                leading: const Icon(Icons.edit),
                title: const Text('Rename'),
                onTap: () async {
                  Navigator.pop(ctx);
                  final name = await nameDialog(
                    'Rename route',
                    route['name'].toString(),
                  );
                  if (name != null) {
                    try {
                      await request('rename', {
                        'id': route['id'],
                        'name': name,
                      });
                      await refresh();
                    } catch (_) {}
                  }
                },
              ),
              ListTile(
                leading: const Icon(Icons.favorite_border),
                title: const Text('Toggle favourite'),
                onTap: () async {
                  Navigator.pop(ctx);
                  try {
                    await request('favorite', {
                      'id': route['id'],
                      'favorite': route['is_favorite'] != true,
                    });
                    await refresh();
                  } catch (_) {}
                },
              ),
              ListTile(
                leading: const Icon(Icons.share),
                title: const Text('Share route'),
                onTap: () async {
                  Navigator.pop(ctx);
                  try {
                    await request('share', {'id': route['id']});
                    message('Route shared with RouteOS drivers.');
                  } catch (_) {}
                },
              ),
              ListTile(
                leading: const Icon(Icons.delete_outline),
                title: const Text('Remove from recent routes'),
                onTap: () async {
                  Navigator.pop(ctx);
                  try {
                    await request('recent.clear', {'id': route['id']});
                    await refresh();
                  } catch (_) {}
                },
              ),
              ListTile(
                leading: const Icon(Icons.delete_outline),
                title: const Text('Delete route'),
                onTap: () async {
                  Navigator.pop(ctx);
                  if (await confirm(
                    'Delete "${route['name']}"?',
                    'This removes the route from RouteOS for everyone. Completed ride history is preserved.',
                  )) {
                    try {
                      await request('delete', {'id': route['id']});
                      await refresh();
                    } catch (_) {}
                  }
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  String km(dynamic n) => '${((n as num? ?? 0) / 1000).toStringAsFixed(1)} km';
  String minutes(dynamic n) => '${((n as num? ?? 0) / 60).ceil()} min';
  String eta(dynamic seconds) {
    if (seconds is! num) return '—';
    final arrival = DateTime.now().add(Duration(seconds: seconds.toInt()));
    return '${arrival.hour.toString().padLeft(2, '0')}:${arrival.minute.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    final loggedIn = (session['id'] as num? ?? 0) > 0;
    final isAdmin = session['role'] == 'admin';
    final landscape =
        MediaQuery.orientationOf(context) == Orientation.landscape;
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) {
        if (!didPop) {
          if (rideStarting) {
            message('Starting navigation — please wait.');
            return;
          }
          if (navigation != null) {
            endRide();
          } else if (page != 'home') {
            changePage('home');
          } else {
            command('close');
          }
        }
      },
      child: Scaffold(
        body: SafeArea(
          child: Column(
            children: [
              Padding(
                padding: EdgeInsets.fromLTRB(
                  16,
                  landscape ? 0 : 12,
                  12,
                  landscape ? 0 : 12,
                ),
                child: Row(
                  children: [
                    if (page != 'home')
                      IconButton(
                        onPressed: () => changePage('home'),
                        icon: const Icon(Icons.arrow_back),
                      ),
                    const Icon(Icons.route, color: Color(0xff10df9b), size: 34),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        page == 'planner'
                            ? 'Draw Route'
                            : page == 'routes'
                            ? 'Saved Routes'
                            : 'RouteOS',
                        style: const TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    IconButton(
                      tooltip: 'Search places',
                      onPressed: searchSheet,
                      icon: const Icon(Icons.search),
                    ),
                    IconButton(
                      tooltip: 'Offline maps',
                      onPressed: () => command('maps.download'),
                      icon: const Icon(Icons.download_for_offline_outlined),
                    ),
                    if (loggedIn)
                      IconButton(
                        tooltip: 'Account',
                        onPressed: () async {
                          if (authRequired) {
                            await login();
                            return;
                          }
                          if (await confirm(
                            'Switch account?',
                            '${session['name']}',
                          )) {
                            try {
                              await request('logout');
                              if (!mounted) return;
                              cancelCalculation();
                              adminTimer?.cancel();
                              planner.restore({'points': []});
                              setState(() {
                                session = {
                                  'development': session['development'],
                                };
                                routes = [];
                                authRequired = false;
                                activeRides = [];
                                page = 'home';
                              });
                            } catch (_) {}
                          }
                        },
                        icon: const Icon(Icons.account_circle_outlined),
                      ),
                  ],
                ),
              ),
              if (authRequired)
                ListTile(
                  dense: true,
                  title: Text(
                    tracking['message']?.toString() ??
                        'Session expired. Sign in to resume syncing.',
                  ),
                  trailing: TextButton(
                    onPressed: login,
                    child: const Text('Sign in'),
                  ),
                ),
              if (error != null)
                Material(
                  color: const Color(0xff213c3a),
                  child: ListTile(
                    dense: true,
                    title: Text(error!),
                    trailing: IconButton(
                      icon: const Icon(Icons.close),
                      onPressed: () => setState(() => error = null),
                    ),
                  ),
                ),
              Expanded(
                child: Stack(
                  children: [
                    const Positioned.fill(child: NativeMap()),
                    Positioned(
                      right: 12,
                      bottom: 18,
                      child: Flex(
                        direction: landscape ? Axis.horizontal : Axis.vertical,
                        children: [
                          FloatingActionButton.small(
                            heroTag: 'plus',
                            tooltip: 'Zoom in',
                            onPressed: () => command('zoom', {'in': true}),
                            child: const Icon(Icons.add),
                          ),
                          const SizedBox(height: 8, width: 8),
                          FloatingActionButton.small(
                            heroTag: 'minus',
                            tooltip: 'Zoom out',
                            onPressed: () => command('zoom', {'in': false}),
                            child: const Icon(Icons.remove),
                          ),
                          const SizedBox(height: 8, width: 8),
                          FloatingActionButton.small(
                            heroTag: 'gps',
                            tooltip: 'My location',
                            onPressed: () => locate(),
                            child: const Icon(Icons.my_location),
                          ),
                        ],
                      ),
                    ),
                    if (!loggedIn) Positioned.fill(child: loginPanel()),
                    if (loggedIn &&
                        session['role'] == 'admin' &&
                        page == 'home')
                      Positioned(
                        left: 12,
                        right: 12,
                        bottom: 12,
                        child: Card(
                          child: SizedBox(
                            height: 220,
                            child: Column(
                              children: [
                                ListTile(
                                  title: const Text('Active drivers'),
                                  subtitle: Text(
                                    '${activeRides.length} live rides',
                                  ),
                                  trailing: IconButton(
                                    tooltip: 'Refresh live rides',
                                    onPressed: pollAdmin,
                                    icon: const Icon(Icons.refresh),
                                  ),
                                ),
                                Expanded(
                                  child: ListView(
                                    children: [
                                      if (activeRides.isEmpty)
                                        const ListTile(
                                          title: Text('No active rides'),
                                          subtitle: Text(
                                            'Drivers appear here when they start a ride.',
                                          ),
                                        ),
                                      for (final ride in activeRides)
                                        ListTile(
                                          leading: const Icon(
                                            Icons.circle,
                                            color: Color(0xff10df9b),
                                            size: 12,
                                          ),
                                          title: Text(
                                            '${ride['driver_name']} · ${ride['location_stale'] == true ? session['tracking_stale_label'] ?? '' : 'LIVE'}',
                                          ),
                                          subtitle: Text(
                                            '${ride['route_name']}\n${ride['vehicle_number']} · GPS ${ride['location_recorded_at'] ?? 'not received'}',
                                          ),
                                          isThreeLine: true,
                                          onTap: ride['latitude'] == null
                                              ? null
                                              : () => command('center', ride),
                                        ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    if (page == 'routes' && loggedIn)
                      Positioned.fill(
                        child: ColoredBox(
                          color: const Color(0xf5081219),
                          child: Column(
                            children: [
                              Padding(
                                padding: const EdgeInsets.all(12),
                                child: TextField(
                                  decoration: const InputDecoration(
                                    hintText: 'Search saved routes',
                                    prefixIcon: Icon(Icons.search),
                                  ),
                                  onChanged: (v) => setState(() => query = v),
                                ),
                              ),
                              Wrap(
                                spacing: 8,
                                children: ['All', 'My Routes', 'Favourites']
                                    .map(
                                      (v) => ChoiceChip(
                                        label: Text(v),
                                        selected: filter == v,
                                        onSelected: (_) =>
                                            setState(() => filter = v),
                                      ),
                                    )
                                    .toList(),
                              ),
                              Expanded(
                                child: RefreshIndicator(
                                  onRefresh: refresh,
                                  child: ListView(
                                    children: [
                                      for (final r in routes.where(
                                        (r) =>
                                            r['name']
                                                .toString()
                                                .toLowerCase()
                                                .contains(
                                                  query.toLowerCase(),
                                                ) &&
                                            (filter != 'My Routes' ||
                                                r['recorder_id'] ==
                                                    session['id']) &&
                                            (filter != 'Favourites' ||
                                                r['is_favorite'] == true),
                                      ))
                                        Card(
                                          child: ListTile(
                                            leading: const Icon(
                                              Icons.route,
                                              color: Color(0xff10df9b),
                                            ),
                                            title: Text(r['name'].toString()),
                                            subtitle: Text(
                                              '${km(r['distance_meters'])} · ${minutes(r['duration_seconds'])}\n${r['recorder_name']}',
                                            ),
                                            isThreeLine: true,
                                            onTap: () => routeActions(r),
                                            trailing: const Icon(
                                              Icons.chevron_right,
                                            ),
                                          ),
                                        ),
                                      if (routes.isEmpty)
                                        const Padding(
                                          padding: EdgeInsets.all(24),
                                          child: Text(
                                            'No saved routes yet. Plan or record your first route.',
                                          ),
                                        ),
                                    ],
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    Positioned(
                      top: 12,
                      left: 12,
                      right: 12,
                      child: NavigationStatusOverlay(
                        navigation: navigationStatus,
                        area: NavigationStatusArea.instruction,
                      ),
                    ),
                    if (moving != null || inserting != null)
                      Positioned(
                        top: 12,
                        left: 12,
                        right: 12,
                        child: Card(
                          child: ListTile(
                            title: Text(
                              moving != null
                                  ? 'Tap the new position for point ${moving! + 1}'
                                  : 'Tap to insert a point',
                            ),
                            trailing: IconButton(
                              onPressed: () => setState(() {
                                moving = null;
                                inserting = null;
                              }),
                              icon: const Icon(Icons.close),
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
              if (loggedIn)
                Padding(
                  padding: EdgeInsets.all(landscape ? 8 : 12),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (recording) ...[
                        Text(
                          'Recording Route · ${km(recordingStats['distance_meters'])} · ${minutes(recordingStats['duration_seconds'])}',
                        ),
                        Row(
                          children: [
                            Expanded(
                              child: OutlinedButton(
                                onPressed: () async {
                                  if (await confirm(
                                    'Discard recording?',
                                    'Stop the native recorder and discard the unsaved track.',
                                  )) {
                                    await command('record.cancel');
                                  }
                                },
                                child: const Text('Discard'),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: FilledButton(
                                onPressed: () => command('record.stop'),
                                child: const Text('Stop & save'),
                              ),
                            ),
                          ],
                        ),
                      ] else if (navigation != null)
                        NavigationStatusOverlay(
                          navigation: navigationStatus,
                          area: NavigationStatusArea.statistics,
                          onEndRide: endRide,
                        )
                      else if (page == 'planner') ...[
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                '${planner.points.length} points · ${planner.state.name.toUpperCase()}',
                              ),
                            ),
                            Text(
                              '${km(planner.distance)} · ${minutes(planner.duration)}',
                            ),
                          ],
                        ),
                        if (planner.points.length >= 4 && !landscape)
                          TextButton.icon(
                            onPressed: optimize,
                            icon: const Icon(Icons.swap_vert),
                            label: const Text('Optimize waypoint order'),
                          ),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                          children: [
                            if (landscape && planner.points.length >= 4)
                              IconButton(
                                tooltip: 'Optimize waypoint order',
                                onPressed: rideStarting ? null : optimize,
                                icon: const Icon(Icons.swap_vert),
                              ),
                            IconButton(
                              tooltip: 'Undo',
                              onPressed: planner.canUndo && !rideStarting
                                  ? () {
                                      planner.undo();
                                      calculate();
                                    }
                                  : null,
                              icon: const Icon(Icons.undo),
                            ),
                            IconButton(
                              tooltip: 'Redo',
                              onPressed: planner.canRedo && !rideStarting
                                  ? () {
                                      planner.redo();
                                      calculate();
                                    }
                                  : null,
                              icon: const Icon(Icons.redo),
                            ),
                            IconButton(
                              tooltip: 'Clear route',
                              onPressed: rideStarting
                                  ? null
                                  : () {
                                      planner.clear();
                                      calculate();
                                    },
                              icon: const Icon(Icons.delete_sweep_outlined),
                            ),
                            IconButton(
                              tooltip: 'Route points',
                              onPressed: rideStarting ? null : pointsSheet,
                              icon: const Icon(Icons.format_list_numbered),
                            ),
                            IconButton(
                              tooltip: 'Use my location as point',
                              onPressed: rideStarting
                                  ? null
                                  : () => locate(add: true),
                              icon: const Icon(Icons.add_location_alt_outlined),
                            ),
                          ],
                        ),
                        Row(
                          children: [
                            Expanded(
                              child: OutlinedButton(
                                onPressed:
                                    planner.state == PlannerState.ready && !busy
                                    ? save
                                    : null,
                                child: const Text('Save route'),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: FilledButton(
                                onPressed:
                                    planner.state == PlannerState.ready && !busy
                                    ? vehicle
                                    : null,
                                child: const Text('Start navigation'),
                              ),
                            ),
                          ],
                        ),
                      ] else if (page == 'home' &&
                          session['role'] != 'admin') ...[
                        Row(
                          children: [
                            Expanded(
                              child: FilledButton.icon(
                                onPressed: () => command('record'),
                                icon: const Icon(Icons.fiber_manual_record),
                                label: const Text('Record route'),
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: OutlinedButton.icon(
                                onPressed: () {
                                  setState(() => page = 'planner');
                                  if (planner.points.isNotEmpty) calculate();
                                },
                                icon: const Icon(Icons.edit_location_alt),
                                label: const Text('Draw route'),
                              ),
                            ),
                          ],
                        ),
                        if (routes.isNotEmpty)
                          ListTile(
                            dense: true,
                            leading: const Icon(Icons.history),
                            title: Text(routes.first['name'].toString()),
                            subtitle: Text(
                              '${km(routes.first['distance_meters'])} · ${minutes(routes.first['duration_seconds'])}',
                            ),
                            onTap: () => routeActions(routes.first),
                          ),
                      ],
                      if (busy || planner.state == PlannerState.calculating)
                        const LinearProgressIndicator(),
                    ],
                  ),
                ),
              if (loggedIn && navigation == null && !recording)
                NavigationBar(
                  height: landscape ? 56 : 80,
                  selectedIndex: page == 'routes' ? 1 : 0,
                  onDestinationSelected: (i) {
                    changePage(
                      (isAdmin
                          ? ['home', 'routes']
                          : ['home', 'routes', 'planner'])[i],
                    );
                  },
                  destinations: [
                    const NavigationDestination(
                      icon: Icon(Icons.home_outlined),
                      label: 'Home',
                    ),
                    const NavigationDestination(
                      icon: Icon(Icons.route),
                      label: 'Routes',
                    ),
                    if (!isAdmin)
                      const NavigationDestination(
                        icon: Icon(Icons.map_outlined),
                        label: 'Draw',
                      ),
                  ],
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget loginPanel() => ColoredBox(
    color: const Color(0xee081219),
    child: Center(
      child: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'Drive. Track. Deliver.',
                style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 12),
              const Text('Your routes. Your road.'),
              const SizedBox(height: 24),
              FilledButton(onPressed: login, child: const Text('Sign in')),
              TextButton(
                onPressed: server,
                child: const Text('Configure server'),
              ),
              if (session['development'] == true) ...[
                const Text('Development accounts'),
                for (final name in [
                  'D.B Cooper',
                  'Sukumara Kurup',
                  'Sreekandan Nair',
                ])
                  Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: FilledButton.tonal(
                      onPressed: () async {
                        try {
                          final user = await request('login', {'name': name});
                          if (!mounted) return;
                          authRequired = false;
                          setState(
                            () => session = {
                              ...session,
                              ...Map<String, dynamic>.from(user as Map),
                            },
                          );
                          await restore();
                        } catch (_) {
                          if (mounted) login(name);
                        }
                      },
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Text(name),
                      ),
                    ),
                  ),
              ],
            ],
          ),
        ),
      ),
    ),
  );
}

enum NavigationStatusArea { instruction, statistics }

class NavigationStatusOverlay extends StatelessWidget {
  const NavigationStatusOverlay({
    required this.navigation,
    required this.area,
    this.onEndRide,
    super.key,
  });

  final ValueListenable<Map<String, dynamic>?> navigation;
  final NavigationStatusArea area;
  final VoidCallback? onEndRide;

  @override
  Widget build(
    BuildContext context,
  ) => ValueListenableBuilder<Map<String, dynamic>?>(
    valueListenable: navigation,
    builder: (context, value, child) {
      if (value == null) return const SizedBox.shrink();
      if (area == NavigationStatusArea.instruction) {
        return Card(
          color: const Color(0xff075f43),
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  value['arrived'] == true
                      ? 'ARRIVED'
                      : _maneuver(value['maneuver']),
                  style: const TextStyle(
                    fontSize: 26,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  '${value['street'] ?? ''} · ${value['turn_distance'] ?? 0} m',
                ),
              ],
            ),
          ),
        );
      }
      return Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  '${_minutes(value['duration_seconds'])} · ${_km(value['distance_meters'])} · ETA ${_eta(value['duration_seconds'])}\n${(value['speed'] as num? ?? 0).round()} km/h${(value['speed_limit'] as num? ?? -1) > 0 ? ' · Limit ${(value['speed_limit'] as num).round()}' : ''}',
                  style: const TextStyle(fontSize: 20),
                ),
                if (value['tracking_message'] != null)
                  Text(
                    value['tracking_message'].toString(),
                    style: const TextStyle(fontSize: 12),
                  ),
              ],
            ),
          ),
          FilledButton(onPressed: onEndRide, child: const Text('End ride')),
        ],
      );
    },
  );

  static String _maneuver(dynamic value) {
    final turn = value?.toString();
    if (turn == null || turn == 'NoTurn') return 'Follow the route';
    return turn.replaceAllMapped(
      RegExp(r'([a-z])([A-Z])'),
      (m) => '${m[1]} ${m[2]}',
    );
  }

  static String _km(dynamic value) =>
      '${((value as num? ?? 0) / 1000).toStringAsFixed(1)} km';

  static String _minutes(dynamic value) =>
      '${((value as num? ?? 0) / 60).ceil()} min';

  static String _eta(dynamic value) {
    if (value is! num) return '—';
    final arrival = DateTime.now().add(Duration(seconds: value.toInt()));
    return '${arrival.hour.toString().padLeft(2, '0')}:${arrival.minute.toString().padLeft(2, '0')}';
  }
}
