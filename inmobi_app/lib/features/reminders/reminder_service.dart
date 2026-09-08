import '../../core/api/odoo_client.dart';
import 'reminder_model.dart';

class ReminderService {
  final OdooClient odoo;
  ReminderService(this.odoo);

  /// [filter] acepta: pending, soon, overdue, done. null = todos.
  Future<List<Reminder>> list({
    int? partnerId,
    String? filter,
    bool myRemindersOnly = false,
    int limit = 80,
  }) async {
    final domain = <dynamic>[];
    if (partnerId != null) {
      domain.add(['partner_id', '=', partnerId]);
    }
    if (myRemindersOnly && odoo.userId != null) {
      domain.add(['user_id', '=', odoo.userId]);
    }

    // Odoo guarda los datetime en UTC, así que los filtros van en UTC.
    final ahora = _nowUtc();
    switch (filter) {
      case 'pending':
        domain.add(['state', '=', 'pending']);
      case 'soon':
        domain.add(['state', '=', 'pending']);
        domain.add(['notify_datetime', '<=', ahora]);
      case 'overdue':
        domain.add(['state', '=', 'pending']);
        domain.add(['deadline', '<', ahora]);
      case 'done':
        domain.add(['state', '=', 'done']);
    }

    final rows = await odoo.searchRead(
      model: 'estate.reminder',
      domain: domain,
      fields: Reminder.fields,
      order: 'deadline asc',
      limit: limit,
    );
    return rows.map(Reminder.fromJson).toList();
  }

  Future<int> countPending({int? partnerId}) async {
    final domain = <dynamic>[
      ['state', '=', 'pending'],
    ];
    if (partnerId != null) {
      domain.add(['partner_id', '=', partnerId]);
    }
    final result = await odoo.callKw(
      model: 'estate.reminder',
      method: 'search_count',
      args: [domain],
    );
    return result as int;
  }

  Future<int> create(Map<String, dynamic> values) =>
      odoo.create(model: 'estate.reminder', values: values);

  Future<void> update(int id, Map<String, dynamic> values) =>
      odoo.write(model: 'estate.reminder', id: id, values: values);

  Future<void> markDone(int id) => update(id, {'state': 'done'});

  Future<void> reopen(int id) => odoo.callKw(
    model: 'estate.reminder',
    method: 'action_reset',
    args: [
      [id],
    ],
  );

  Future<void> delete(int id) => odoo.unlink(model: 'estate.reminder', id: id);

  static String _nowUtc() {
    final n = DateTime.now().toUtc();
    return '${formatDate(n)} '
        '${n.hour.toString().padLeft(2, '0')}:'
        '${n.minute.toString().padLeft(2, '0')}:'
        '${n.second.toString().padLeft(2, '0')}';
  }

  static String formatDate(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-'
      '${d.month.toString().padLeft(2, '0')}-'
      '${d.day.toString().padLeft(2, '0')}';
}
