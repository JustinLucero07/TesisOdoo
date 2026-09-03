import '../../core/api/odoo_client.dart';
import '../../core/notifications/notification_service.dart';
import 'visit_model.dart';

class VisitService {
  final OdooClient odoo;
  VisitService(this.odoo);

  static Future<void> scheduleNotifications(
    List<Visit> visits, {
    int? currentUserId,
  }) async {
    final notifier = NotificationService.instance;
    if (!notifier.enabled) return;
    for (final v in visits) {
      final isMyVisit =
          currentUserId == null ||
          v.userId == null ||
          v.userId == currentUserId;
      if (!isMyVisit ||
          v.visitState != 'scheduled' ||
          !v.start.isAfter(DateTime.now())) {
        await notifier.cancelVisit(v.id);
        continue;
      }
      final minutes = v.reminderValue > 0
          ? v.reminderValue * _unitMultiplier(v.reminderUnit)
          : 60;
      await notifier.scheduleVisit(
        visitId: v.id,
        title:
            '${AppointmentTypeStyle.label(v.appointmentType)} en ${_inWords(minutes)}',
        body: [
          if (v.propertyName.isNotEmpty) v.propertyName else v.name,
          if (v.clientName.isNotEmpty) 'Cliente: ${v.clientName}',
        ].join(' · '),
        start: v.start,
        minutesBefore: minutes,
      );
    }
  }

  static Future<void> scheduleAllUpcoming(
    OdooClient odoo, {
    int? currentUserId,
  }) async {
    try {
      final now = DateTime.now();
      final domain = <dynamic>[
        ['start', '>=', formatUtc(now)],
        ['appointment_type', '!=', false],
        ['visit_state', '=', 'scheduled'],
      ];
      if (currentUserId != null) {
        domain.addAll([
          '|',
          ['user_id', '=', currentUserId],
          ['user_id', '=', false],
        ]);
      }
      final rows = await odoo.searchRead(
        model: 'calendar.event',
        domain: domain,
        fields: Visit.listFields,
        order: 'start asc',
        limit: 100,
      );
      final visits = rows.map(Visit.fromJson).toList();
      await scheduleNotifications(visits, currentUserId: currentUserId);
    } catch (_) {}
  }

  static int _unitMultiplier(String unit) => switch (unit) {
    'hours' => 60,
    'days' => 1440,
    _ => 1,
  };

  static String _inWords(int minutes) {
    if (minutes < 60) return '$minutes minutos';
    if (minutes < 1440) {
      final h = minutes ~/ 60;
      return h == 1 ? '1 hora' : '$h horas';
    }
    final d = minutes ~/ 1440;
    return d == 1 ? '1 día' : '$d días';
  }

  static String formatUtc(DateTime d) =>
      d.toUtc().toIso8601String().substring(0, 19).replaceFirst('T', ' ');

  Future<List<Visit>> listByRange(
    DateTime from,
    DateTime to, {
    String? visitState,
    String? visitResult,
    String? appointmentType,
    int? advisorId,
    bool myVisitsOnly = false,
    int? currentUserId,
  }) async {
    final domain = <dynamic>[
      ['start', '>=', formatUtc(from)],
      ['start', '<=', formatUtc(to)],
      ['appointment_type', '!=', false],
    ];

    if (visitState != null && visitState.isNotEmpty) {
      domain.add(['visit_state', '=', visitState]);
    }
    if (visitResult != null && visitResult.isNotEmpty) {
      domain.add(['visit_result', '=', visitResult]);
    }
    if (appointmentType != null && appointmentType.isNotEmpty) {
      domain.add(['appointment_type', '=', appointmentType]);
    }
    if (advisorId != null) {
      domain.add(['user_id', '=', advisorId]);
    } else if (myVisitsOnly && currentUserId != null) {
      domain.add(['user_id', '=', currentUserId]);
    }

    final rows = await odoo.searchRead(
      model: 'calendar.event',
      domain: domain,
      fields: Visit.listFields,
      order: 'start asc',
      limit: 200,
    );
    return rows.map(Visit.fromJson).toList();
  }

  Future<int> countToday() async {
    final now = DateTime.now();
    final from = DateTime(now.year, now.month, now.day);
    final to = from.add(const Duration(days: 1));
    final visits = await listByRange(from, to);
    return visits.length;
  }

  Future<List<Visit>> listForLead({
    int? leadId,
    int? partnerId,
    int? propertyId,
  }) async {
    final domain = <dynamic>[
      ['appointment_type', '!=', false],
    ];
    if (partnerId != null && propertyId != null) {
      domain.addAll([
        '|',
        [
          'partner_ids',
          'in',
          [partnerId],
        ],
        ['property_id', '=', propertyId],
      ]);
    } else if (partnerId != null) {
      domain.add([
        'partner_ids',
        'in',
        [partnerId],
      ]);
    } else if (propertyId != null) {
      domain.add(['property_id', '=', propertyId]);
    }
    final rows = await odoo.searchRead(
      model: 'calendar.event',
      domain: domain,
      fields: Visit.listFields,
      order: 'start desc',
      limit: 50,
    );
    return rows.map(Visit.fromJson).toList();
  }

  Future<int> create(Map<String, dynamic> values) =>
      odoo.create(model: 'calendar.event', values: values);

  Future<void> update(int id, Map<String, dynamic> values) =>
      odoo.write(model: 'calendar.event', id: id, values: values);
}
