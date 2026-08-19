import '../../core/api/odoo_client.dart';
import 'visit_model.dart';

class VisitService {
  final OdooClient odoo;
  VisitService(this.odoo);

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
