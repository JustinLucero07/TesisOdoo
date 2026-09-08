import 'package:flutter/material.dart';

import '../../core/api/odoo_json.dart';
import '../../core/theme/app_theme.dart';

class Reminder {
  final int id;
  final String name;
  final String reminderType;
  final int? partnerId;
  final String partnerName;
  final int? propertyId;
  final String propertyName;
  final int? leadId;
  final String leadName;
  final DateTime? date;
  final int daysBefore;
  final DateTime? notifyDate;
  final int? userId;
  final String userName;
  final bool notifyPush;
  final String state;
  final bool advanceNotified;
  final bool dueNotified;
  final String note;

  Reminder({
    required this.id,
    required this.name,
    this.reminderType = 'other',
    this.partnerId,
    this.partnerName = '',
    this.propertyId,
    this.propertyName = '',
    this.leadId,
    this.leadName = '',
    this.date,
    this.daysBefore = 7,
    this.notifyDate,
    this.userId,
    this.userName = '',
    this.notifyPush = true,
    this.state = 'pending',
    this.advanceNotified = false,
    this.dueNotified = false,
    this.note = '',
  });

  static const List<String> fields = [
    'name',
    'reminder_type',
    'partner_id',
    'property_id',
    'lead_id',
    'date',
    'days_before',
    'notify_date',
    'user_id',
    'notify_push',
    'state',
    'advance_notified',
    'due_notified',
    'note',
  ];

  factory Reminder.fromJson(Map<String, dynamic> j) => Reminder(
    id: j['id'] as int,
    name: asOdooString(j['name']),
    reminderType: asOdooString(j['reminder_type'], 'other'),
    partnerId: j['partner_id'] is List ? j['partner_id'][0] as int : null,
    partnerName: many2oneName(j['partner_id']),
    propertyId: j['property_id'] is List ? j['property_id'][0] as int : null,
    propertyName: many2oneName(j['property_id']),
    leadId: j['lead_id'] is List ? j['lead_id'][0] as int : null,
    leadName: many2oneName(j['lead_id']),
    date: j['date'] is String ? DateTime.tryParse(j['date']) : null,
    daysBefore: asOdooInt(j['days_before'], 7),
    notifyDate: j['notify_date'] is String
        ? DateTime.tryParse(j['notify_date'])
        : null,
    userId: j['user_id'] is List ? j['user_id'][0] as int : null,
    userName: many2oneName(j['user_id']),
    notifyPush: j['notify_push'] != false,
    state: asOdooString(j['state'], 'pending'),
    advanceNotified: j['advance_notified'] == true,
    dueNotified: j['due_notified'] == true,
    note: asOdooString(j['note']),
  );

  /// Días que faltan para la fecha. Negativo = ya venció.
  int get daysLeft {
    if (date == null) return 0;
    final hoy = DateTime.now();
    final d = DateTime(date!.year, date!.month, date!.day);
    return d.difference(DateTime(hoy.year, hoy.month, hoy.day)).inDays;
  }

  bool get isPending => state == 'pending';
  bool get isOverdue => isPending && daysLeft < 0;
  bool get isToday => isPending && daysLeft == 0;

  String get countdownLabel {
    if (!isPending) return ReminderStateStyle.label(state);
    final d = daysLeft;
    if (d < 0) return 'Venció hace ${-d} ${-d == 1 ? 'día' : 'días'}';
    if (d == 0) return 'Vence hoy';
    if (d == 1) return 'Vence mañana';
    return 'En $d días';
  }
}

class ReminderTypeStyle {
  static const List<(String, String)> options = [
    ('policy', 'Póliza / Seguro'),
    ('payment', 'Pago o cuota'),
    ('document', 'Documento por vencer'),
    ('contract', 'Contrato / Renovación'),
    ('followup', 'Seguimiento comercial'),
    ('birthday', 'Cumpleaños'),
    ('other', 'Otro'),
  ];

  static String label(String t) =>
      options.firstWhere((o) => o.$1 == t, orElse: () => ('other', 'Otro')).$2;

  static IconData icon(String t) => switch (t) {
    'policy' => Icons.shield_outlined,
    'payment' => Icons.payments_outlined,
    'document' => Icons.description_outlined,
    'contract' => Icons.handshake_outlined,
    'followup' => Icons.phone_in_talk_outlined,
    'birthday' => Icons.cake_outlined,
    _ => Icons.notifications_active_outlined,
  };
}

class ReminderStateStyle {
  static String label(String s) => switch (s) {
    'done' => 'Hecho',
    'cancelled' => 'Cancelado',
    _ => 'Pendiente',
  };

  static Color color(String s, AppPalette colors) => switch (s) {
    'done' => colors.success,
    'cancelled' => colors.mutedLight,
    _ => colors.info,
  };

  /// El color del contador depende de lo cerca que esté la fecha, no del estado.
  static Color urgencyColor(Reminder r, AppPalette colors) {
    if (!r.isPending) return colors.mutedLight;
    if (r.isOverdue) return colors.danger;
    if (r.daysLeft <= r.daysBefore) return colors.warning;
    return colors.muted;
  }
}
