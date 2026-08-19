import '../../core/api/odoo_client.dart';
import '../../core/notifications/notification_service.dart';
import 'visit_model.dart';

class VisitService {
  final OdooClient odoo;
  VisitService(this.odoo);

  /// Programa en el teléfono el aviso de cada cita futura que siga
  /// programada. Se llama al cargar la agenda: así el asesor recibe la
  /// notificación aunque después cierre la app o se quede sin señal.
  static Future<void> scheduleNotifications(List<Visit> visits) async {
    final notifier = NotificationService.instance;
    if (!notifier.enabled) return;
    for (final v in visits) {
      if (v.visitState != 'scheduled' || !v.start.isAfter(DateTime.now())) {
        // Cancelada, realizada o ya pasada: si tenía aviso, se retira.
        await notifier.cancelVisit(v.id);
        continue;
      }
      final minutes = v.reminderValue > 0
          ? v.reminderValue * _unitMultiplier(v.reminderUnit)
          : 60; // por defecto, una hora antes
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

  /// Odoo guarda las fechas en UTC como "yyyy-MM-dd HH:mm:ss" — se usa tanto
  /// para filtrar (listByRange) como para mandar start/stop al crear/editar.
  static String formatUtc(DateTime d) =>
      d.toUtc().toIso8601String().substring(0, 19).replaceFirst('T', ' ');

  /// Trae las visitas entre [from] y [to] (inclusive), ordenadas por hora.
  Future<List<Visit>> listByRange(DateTime from, DateTime to) async {
    final rows = await odoo.searchRead(
      model: 'calendar.event',
      domain: [
        ['start', '>=', formatUtc(from)],
        ['start', '<=', formatUtc(to)],
        ['appointment_type', '!=', false],
      ],
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

  Future<int> create(Map<String, dynamic> values) =>
      odoo.create(model: 'calendar.event', values: values);

  Future<void> update(int id, Map<String, dynamic> values) =>
      odoo.write(model: 'calendar.event', id: id, values: values);
}
