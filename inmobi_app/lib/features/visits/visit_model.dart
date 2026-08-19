import 'package:flutter/material.dart';

import '../../core/api/odoo_json.dart';
import '../../core/theme/app_theme.dart';

class Visit {
  final int id;
  final String name;
  final DateTime start;
  final String appointmentType; // visit | meeting | call | signing
  final String visitState; // scheduled | done | cancelled
  final int? propertyId;
  final String propertyName;
  final int? clientId;
  final String clientName;
  final String notes;

  Visit({
    required this.id,
    required this.name,
    required this.start,
    required this.appointmentType,
    required this.visitState,
    this.propertyId,
    required this.propertyName,
    this.clientId,
    required this.clientName,
    required this.notes,
  });

  static const List<String> listFields = [
    'name',
    'start',
    'appointment_type',
    'visit_state',
    'property_id',
    'client_id',
    'visit_notes',
  ];

  factory Visit.fromJson(Map<String, dynamic> json) {
    return Visit(
      id: json['id'] as int,
      name: asOdooString(json['name']),
      // Odoo devuelve la fecha en UTC como "yyyy-MM-dd HH:mm:ss".
      start: DateTime.parse(
        '${asOdooString(json['start']).replaceFirst(' ', 'T')}Z',
      ).toLocal(),
      appointmentType: asOdooString(json['appointment_type'], 'visit'),
      visitState: asOdooString(json['visit_state'], 'scheduled'),
      propertyId: json['property_id'] is List
          ? json['property_id'][0] as int
          : null,
      propertyName: many2oneName(json['property_id']),
      clientId: json['client_id'] is List ? json['client_id'][0] as int : null,
      clientName: many2oneName(json['client_id']),
      notes: asOdooString(json['visit_notes']),
    );
  }
}

class VisitStateStyle {
  static String label(String state) => switch (state) {
    'done' => 'Realizada',
    'cancelled' => 'Cancelada',
    _ => 'Programada',
  };

  static Color color(String state) => switch (state) {
    'done' => AppColors.success,
    'cancelled' => AppColors.danger,
    _ => AppColors.info,
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
}
