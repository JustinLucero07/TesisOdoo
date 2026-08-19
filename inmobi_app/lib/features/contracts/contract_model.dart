import 'package:flutter/material.dart';

import '../../core/api/odoo_json.dart';
import '../../core/theme/app_theme.dart';

class Contract {
  final int id;
  final String reference;
  final int? propertyId;
  final String propertyName;
  final int? partnerId;
  final String partnerName;
  final String contractType;
  final String state;
  final DateTime? dateStart;
  final DateTime? dateEnd;
  final double amount;
  final double commissionPercentage;

  Contract({
    required this.id,
    required this.reference,
    this.propertyId,
    required this.propertyName,
    this.partnerId,
    required this.partnerName,
    required this.contractType,
    required this.state,
    this.dateStart,
    this.dateEnd,
    required this.amount,
    required this.commissionPercentage,
  });

  static const List<String> listFields = [
    'name',
    'property_id',
    'partner_id',
    'contract_type',
    'state',
    'date_start',
    'date_end',
    'amount',
    'commission_percentage',
  ];

  factory Contract.fromJson(Map<String, dynamic> json) {
    DateTime? parseDate(dynamic v) => v is String ? DateTime.tryParse(v) : null;
    return Contract(
      id: json['id'] as int,
      reference: asOdooString(json['name']),
      propertyId: json['property_id'] is List
          ? json['property_id'][0] as int
          : null,
      propertyName: many2oneName(json['property_id']),
      partnerId: json['partner_id'] is List
          ? json['partner_id'][0] as int
          : null,
      partnerName: many2oneName(json['partner_id']),
      contractType: asOdooString(json['contract_type'], 'exclusive_owner'),
      state: asOdooString(json['state'], 'draft'),
      dateStart: parseDate(json['date_start']),
      dateEnd: parseDate(json['date_end']),
      amount: asOdooDouble(json['amount']),
      commissionPercentage: asOdooDouble(json['commission_percentage']),
    );
  }
}

class ContractStateStyle {
  static String label(String state) => switch (state) {
    'active' => 'Activo',
    'suspended' => 'Suspendido',
    'renewing' => 'En renovación',
    'renewed' => 'Renovado',
    'expired' => 'Vencido',
    'cancelled' => 'Cancelado',
    _ => 'Borrador',
  };

  static Color color(String state) => switch (state) {
    'active' => AppColors.success,
    'suspended' || 'renewing' => AppColors.warning,
    'expired' || 'cancelled' => AppColors.danger,
    'renewed' => AppColors.info,
    _ => AppColors.muted,
  };
}

class ContractTypeStyle {
  static String label(String type) => switch (type) {
    'exclusive_owner' => 'Exclusividad (Propietario)',
    'exclusive_proxy' => 'Exclusividad (Apoderado)',
    'non_exclusive_owner' => 'Sin exclusividad (Propietario)',
    'non_exclusive_proxy' => 'Sin exclusividad (Apoderado)',
    'no_contract' => 'Sin contrato',
    'sale' => 'Compraventa',
    'rent' => 'Arriendo',
    'exclusive' => 'Exclusividad',
    _ => type,
  };

  static const List<(String, String)> options = [
    ('exclusive_owner', 'Exclusividad (Propietario)'),
    ('exclusive_proxy', 'Exclusividad (Apoderado)'),
    ('non_exclusive_owner', 'Sin exclusividad (Propietario)'),
    ('non_exclusive_proxy', 'Sin exclusividad (Apoderado)'),
    ('no_contract', 'Sin contrato'),
    ('sale', 'Compraventa (General)'),
    ('rent', 'Arriendo (General)'),
    ('exclusive', 'Exclusividad (General)'),
  ];
}
