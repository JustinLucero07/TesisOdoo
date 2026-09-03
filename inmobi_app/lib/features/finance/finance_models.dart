import 'package:flutter/material.dart';

import '../../core/api/odoo_json.dart';
import '../../core/theme/app_theme.dart';

/// `estate.commission` — lo que el asesor gana por cada cierre.
class Commission {
  final int id;
  final String reference;
  final String propertyName;
  final String userName;
  final String leadName;
  final double saleAmount;
  final double commissionPct;
  final double amount;
  final String type;
  final String state;
  final DateTime? date;
  final DateTime? paymentDate;

  Commission({
    required this.id,
    required this.reference,
    this.propertyName = '',
    this.userName = '',
    this.leadName = '',
    this.saleAmount = 0,
    this.commissionPct = 0,
    this.amount = 0,
    this.type = 'sale',
    this.state = 'draft',
    this.date,
    this.paymentDate,
  });

  static const List<String> fields = [
    'name',
    'property_id',
    'user_id',
    'lead_id',
    'sale_amount',
    'commission_pct',
    'amount',
    'type',
    'state',
    'date',
    'payment_date',
  ];

  factory Commission.fromJson(Map<String, dynamic> j) => Commission(
    id: j['id'] as int,
    reference: asOdooString(j['name']),
    propertyName: many2oneName(j['property_id']),
    userName: many2oneName(j['user_id']),
    leadName: many2oneName(j['lead_id']),
    saleAmount: asOdooDouble(j['sale_amount']),
    commissionPct: asOdooDouble(j['commission_pct']),
    amount: asOdooDouble(j['amount']),
    type: asOdooString(j['type'], 'sale'),
    state: asOdooString(j['state'], 'draft'),
    date: j['date'] is String ? DateTime.tryParse(j['date']) : null,
    paymentDate: j['payment_date'] is String
        ? DateTime.tryParse(j['payment_date'])
        : null,
  );

  static String stateLabel(String s) => switch (s) {
    'approved' => 'Aprobada',
    'paid' => 'Pagada',
    'cancelled' => 'Anulada',
    _ => 'Borrador',
  };

  static Color stateColor(String s, AppPalette colors) => switch (s) {
    'approved' => colors.info,
    'paid' => colors.success,
    'cancelled' => colors.danger,
    _ => colors.mutedLight,
  };

  static String typeLabel(String t) => switch (t) {
    'rent' => 'Arriendo (1er mes)',
    'bonus' => 'Bono / Premio',
    _ => 'Venta',
  };
}

/// `estate.payment` — cuotas y pagos de un contrato.
class Payment {
  final int id;
  final String reference;
  final String contractName;
  final String propertyName;
  final String partnerName;
  final double amount;
  final String method;
  final String state;
  final DateTime? date;
  final String notes;

  Payment({
    required this.id,
    required this.reference,
    this.contractName = '',
    this.propertyName = '',
    this.partnerName = '',
    this.amount = 0,
    this.method = 'bank',
    this.state = 'pending',
    this.date,
    this.notes = '',
  });

  static const List<String> fields = [
    'name',
    'contract_id',
    'property_id',
    'partner_id',
    'amount',
    'payment_method',
    'state',
    'date',
    'notes',
  ];

  factory Payment.fromJson(Map<String, dynamic> j) => Payment(
    id: j['id'] as int,
    reference: asOdooString(j['name']),
    contractName: many2oneName(j['contract_id']),
    propertyName: many2oneName(j['property_id']),
    partnerName: many2oneName(j['partner_id']),
    amount: asOdooDouble(j['amount']),
    method: asOdooString(j['payment_method'], 'bank'),
    state: asOdooString(j['state'], 'pending'),
    date: j['date'] is String ? DateTime.tryParse(j['date']) : null,
    notes: asOdooString(j['notes']),
  );

  static String stateLabel(String s) => switch (s) {
    'paid' => 'Pagado',
    'cancelled' => 'Anulado',
    _ => 'Pendiente',
  };

  static Color stateColor(String s, AppPalette colors) => switch (s) {
    'paid' => colors.success,
    'cancelled' => colors.danger,
    _ => colors.warning,
  };

  static String methodLabel(String m) => switch (m) {
    'cash' => 'Efectivo',
    'check' => 'Cheque',
    'card' => 'Tarjeta',
    'other' => 'Otro',
    _ => 'Transferencia',
  };

  static const List<(String, String)> methodOptions = [
    ('bank', 'Transferencia bancaria'),
    ('cash', 'Efectivo'),
    ('check', 'Cheque'),
    ('card', 'Tarjeta'),
    ('other', 'Otro'),
  ];
}

/// `estate.property.expense` — gastos imputados a una propiedad.
class Expense {
  final int id;
  final String name;
  final int? propertyId;
  final String propertyName;
  final String expenseType;
  final double amount;
  final String paidBy;
  final bool reimbursable;
  final bool reimbursed;
  final String state;
  final DateTime? date;
  final String notes;

  Expense({
    required this.id,
    required this.name,
    this.propertyId,
    this.propertyName = '',
    this.expenseType = 'other',
    this.amount = 0,
    this.paidBy = '',
    this.reimbursable = false,
    this.reimbursed = false,
    this.state = 'draft',
    this.date,
    this.notes = '',
  });

  static const List<String> fields = [
    'name',
    'property_id',
    'expense_type',
    'amount',
    'paid_by',
    'reimbursable',
    'reimbursed',
    'state',
    'date',
    'notes',
  ];

  factory Expense.fromJson(Map<String, dynamic> j) => Expense(
    id: j['id'] as int,
    name: asOdooString(j['name']),
    propertyId: j['property_id'] is List ? j['property_id'][0] as int : null,
    propertyName: many2oneName(j['property_id']),
    expenseType: asOdooString(j['expense_type'], 'other'),
    amount: asOdooDouble(j['amount']),
    paidBy: asOdooString(j['paid_by']),
    reimbursable: j['reimbursable'] == true,
    reimbursed: j['reimbursed'] == true,
    state: asOdooString(j['state'], 'draft'),
    date: j['date'] is String ? DateTime.tryParse(j['date']) : null,
    notes: asOdooString(j['notes']),
  );

  static Color stateColor(String s, AppPalette colors) => switch (s) {
    'approved' || 'paid' => colors.success,
    'cancelled' => colors.danger,
    _ => colors.mutedLight,
  };
}

/// `estate.appraisal` — tasaciones solicitadas sobre una propiedad.
class Appraisal {
  final int id;
  final String reference;
  final String propertyName;
  final String partnerName;
  final String userName;
  final double marketValue;
  final double commercialValue;
  final double currentPrice;
  final double variancePct;
  final String state;
  final DateTime? dateRequested;
  final DateTime? dateCompleted;

  Appraisal({
    required this.id,
    required this.reference,
    this.propertyName = '',
    this.partnerName = '',
    this.userName = '',
    this.marketValue = 0,
    this.commercialValue = 0,
    this.currentPrice = 0,
    this.variancePct = 0,
    this.state = 'draft',
    this.dateRequested,
    this.dateCompleted,
  });

  static const List<String> fields = [
    'name',
    'property_id',
    'partner_id',
    'user_id',
    'market_value',
    'commercial_value',
    'current_price',
    'price_variance_pct',
    'state',
    'date_requested',
    'date_completed',
  ];

  factory Appraisal.fromJson(Map<String, dynamic> j) => Appraisal(
    id: j['id'] as int,
    reference: asOdooString(j['name']),
    propertyName: many2oneName(j['property_id']),
    partnerName: many2oneName(j['partner_id']),
    userName: many2oneName(j['user_id']),
    marketValue: asOdooDouble(j['market_value']),
    commercialValue: asOdooDouble(j['commercial_value']),
    currentPrice: asOdooDouble(j['current_price']),
    variancePct: asOdooDouble(j['price_variance_pct']),
    state: asOdooString(j['state'], 'draft'),
    dateRequested: j['date_requested'] is String
        ? DateTime.tryParse(j['date_requested'])
        : null,
    dateCompleted: j['date_completed'] is String
        ? DateTime.tryParse(j['date_completed'])
        : null,
  );

  static String stateLabel(String s) => switch (s) {
    'requested' => 'Solicitada',
    'scheduled' => 'Programada',
    'in_progress' => 'En proceso',
    'completed' => 'Completada',
    'cancelled' => 'Cancelada',
    _ => 'Borrador',
  };

  static Color stateColor(String s, AppPalette colors) => switch (s) {
    'completed' => colors.success,
    'cancelled' => colors.danger,
    'in_progress' || 'scheduled' => colors.warning,
    _ => colors.mutedLight,
  };
}

/// `estate.property.price.history` — bitácora de cambios de precio.
class PriceChange {
  final int id;
  final DateTime? date;
  final double oldPrice;
  final double newPrice;
  final double changePct;
  final String reason;
  final String userName;

  PriceChange({
    required this.id,
    this.date,
    this.oldPrice = 0,
    this.newPrice = 0,
    this.changePct = 0,
    this.reason = '',
    this.userName = '',
  });

  static const List<String> fields = [
    'date',
    'old_price',
    'new_price',
    'change_pct',
    'change_reason',
    'user_id',
  ];

  factory PriceChange.fromJson(Map<String, dynamic> j) => PriceChange(
    id: j['id'] as int,
    date: j['date'] is String
        ? DateTime.tryParse((j['date'] as String).replaceFirst(' ', 'T'))
        : null,
    oldPrice: asOdooDouble(j['old_price']),
    newPrice: asOdooDouble(j['new_price']),
    changePct: asOdooDouble(j['change_pct']),
    reason: asOdooString(j['change_reason']),
    userName: many2oneName(j['user_id']),
  );

  bool get isDrop => newPrice < oldPrice;
}
