import 'package:flutter/material.dart';

import '../../core/api/odoo_json.dart';
import '../../core/theme/app_theme.dart';

class Visit {
  final int id;
  final String name;
  final DateTime start;
  final DateTime? stop;
  final String appointmentType;
  final String visitState;
  final int? propertyId;
  final String propertyName;
  final int? clientId;
  final String clientName;
  final int? userId;
  final String userName;
  final String notes;
  final String description;
  final String location;
  final bool allDay;
  final String visitResult;
  final String visitRating;
  final bool whatsappSent;
  final int reminderValue;
  final String reminderUnit;
  final List<String> attendeeNames;

  Visit({
    required this.id,
    required this.name,
    required this.start,
    this.stop,
    required this.appointmentType,
    required this.visitState,
    this.propertyId,
    required this.propertyName,
    this.clientId,
    required this.clientName,
    this.userId,
    this.userName = '',
    required this.notes,
    this.description = '',
    this.location = '',
    this.allDay = false,
    this.visitResult = '',
    this.visitRating = '',
    this.whatsappSent = false,
    this.reminderValue = 0,
    this.reminderUnit = 'minutes',
    this.attendeeNames = const [],
  });

  Duration? get duration => stop == null ? null : stop!.difference(start);

  static const List<String> listFields = [
    'name',
    'start',
    'appointment_type',
    'visit_state',
    'property_id',
    'client_id',
    'user_id',
    'visit_notes',
    'visit_result',
    'visit_rating',

    'whatsapp_reminder_value',
    'whatsapp_reminder_unit',
  ];

  static const List<String> detailFields = [
    ...listFields,
    'stop',
    'user_id',
    'description',
    'location',
    'allday',
    'whatsapp_sent',
    'partner_ids',
  ];

  factory Visit.fromJson(Map<String, dynamic> json) {
    DateTime parseOdoo(String raw) =>
        DateTime.parse('${raw.replaceFirst(' ', 'T')}Z').toLocal();
    return Visit(
      id: json['id'] as int,
      name: asOdooString(json['name']),

      start: parseOdoo(asOdooString(json['start'])),
      stop: json['stop'] is String ? parseOdoo(json['stop'] as String) : null,
      appointmentType: asOdooString(json['appointment_type'], 'visit'),
      visitState: asOdooString(json['visit_state'], 'scheduled'),
      propertyId: json['property_id'] is List
          ? json['property_id'][0] as int
          : null,
      propertyName: many2oneName(json['property_id']),
      clientId: json['client_id'] is List ? json['client_id'][0] as int : null,
      clientName: many2oneName(json['client_id']),
      userId: json['user_id'] is List ? json['user_id'][0] as int : null,
      userName: many2oneName(json['user_id']),
      notes: asOdooString(json['visit_notes']),

      description: asOdooString(json['description'])
          .replaceAll(RegExp(r'<br\s*/?>', caseSensitive: false), '\n')
          .replaceAll(RegExp(r'</p>', caseSensitive: false), '\n')
          .replaceAll(RegExp(r'<[^>]*>'), '')
          .replaceAll(RegExp(r'\n{3,}'), '\n\n')
          .trim(),
      location: asOdooString(json['location']),
      allDay: json['allday'] == true,
      visitResult: asOdooString(json['visit_result']),
      visitRating: asOdooString(json['visit_rating']),
      whatsappSent: json['whatsapp_sent'] == true,
      reminderValue: asOdooInt(json['whatsapp_reminder_value']),
      reminderUnit: asOdooString(json['whatsapp_reminder_unit'], 'minutes'),

      attendeeNames: const [],
    );
  }

  Visit copyWithAttendees(List<String> names) => Visit(
    id: id,
    name: name,
    start: start,
    stop: stop,
    appointmentType: appointmentType,
    visitState: visitState,
    propertyId: propertyId,
    propertyName: propertyName,
    clientId: clientId,
    clientName: clientName,
    userId: userId,
    userName: userName,
    notes: notes,
    description: description,
    location: location,
    allDay: allDay,
    visitResult: visitResult,
    visitRating: visitRating,
    whatsappSent: whatsappSent,
    reminderValue: reminderValue,
    reminderUnit: reminderUnit,
    attendeeNames: names,
  );
}

class VisitStateStyle {
  static String label(String state) => switch (state) {
    'done' => 'Realizada',
    'cancelled' => 'Cancelada',
    _ => 'Programada',
  };

  static Color color(String state, AppPalette colors) => switch (state) {
    'done' => colors.success,
    'cancelled' => colors.danger,
    _ => colors.info,
  };
}

class AppointmentTypeStyle {
  static String label(String type) => switch (type) {
    'meeting' => 'Reunión',
    'call' => 'Llamada',
    'signing' => 'Firma de contrato',
    _ => 'Visita',
  };

  static IconData icon(String type) => switch (type) {
    'meeting' => Icons.groups_outlined,
    'call' => Icons.call_outlined,
    'signing' => Icons.edit_document,
    _ => Icons.home_outlined,
  };

  static Color color(String type, AppPalette colors) => switch (type) {
    'meeting' => colors.navyLight,
    'call' => colors.info,
    'signing' => colors.accent,
    _ => colors.navy,
  };
}

class VisitResultStyle {
  static String label(String r) => switch (r) {
    'interested' => 'Interesado',
    'not_interested' => 'No interesado',
    'follow_up' => 'Seguimiento',
    'offer_made' => 'Oferta realizada',
    _ => '',
  };

  static Color color(String r, AppPalette colors) => switch (r) {
    'interested' => colors.success,
    'offer_made' => colors.navy,
    'follow_up' => colors.warning,
    'not_interested' => colors.danger,
    _ => colors.mutedLight,
  };

  static const List<(String, String)> options = [
    ('interested', 'Interesado'),
    ('follow_up', 'Seguimiento'),
    ('offer_made', 'Oferta realizada'),
    ('not_interested', 'No interesado'),
  ];
}

class ReminderUnitStyle {
  static String label(String u) => switch (u) {
    'hours' => 'horas',
    'days' => 'días',
    _ => 'minutos',
  };

  static const List<(String, String)> options = [
    ('minutes', 'Minutos'),
    ('hours', 'Horas'),
    ('days', 'Días'),
  ];
}
