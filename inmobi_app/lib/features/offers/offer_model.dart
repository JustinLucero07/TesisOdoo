import 'package:flutter/material.dart';

import '../../core/api/odoo_json.dart';
import '../../core/theme/app_theme.dart';

/// Espejo de `estate.property.offer` — la negociación entre el interesado y
/// el propietario: monto ofertado, contraoferta y precio final acordado.
class Offer {
  final int id;
  final String reference;
  final int? propertyId;
  final String propertyName;
  final int? partnerId;
  final String partnerName;
  final int? leadId;
  final String leadName;
  final double askingPrice;
  final double offerAmount;
  final double counterofferAmount;
  final double finalAgreedAmount;
  final double discountPct;
  final String financingType;
  final String state;
  final DateTime? date;
  final DateTime? dateExpiry;
  final String notes;

  Offer({
    required this.id,
    required this.reference,
    this.propertyId,
    this.propertyName = '',
    this.partnerId,
    this.partnerName = '',
    this.leadId,
    this.leadName = '',
    this.askingPrice = 0,
    this.offerAmount = 0,
    this.counterofferAmount = 0,
    this.finalAgreedAmount = 0,
    this.discountPct = 0,
    this.financingType = 'cash',
    this.state = 'draft',
    this.date,
    this.dateExpiry,
    this.notes = '',
  });

  static const List<String> fields = [
    'name',
    'property_id',
    'partner_id',
    'lead_id',
    'asking_price',
    'offer_amount',
    'counteroffer_amount',
    'final_agreed_amount',
    'discount_pct',
    'financing_type',
    'state',
    'date',
    'date_expiry',
    'notes',
  ];

  factory Offer.fromJson(Map<String, dynamic> json) {
    DateTime? parseDate(dynamic v) => v is String ? DateTime.tryParse(v) : null;
    return Offer(
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
      leadId: json['lead_id'] is List ? json['lead_id'][0] as int : null,
      leadName: many2oneName(json['lead_id']),
      askingPrice: asOdooDouble(json['asking_price']),
      offerAmount: asOdooDouble(json['offer_amount']),
      counterofferAmount: asOdooDouble(json['counteroffer_amount']),
      finalAgreedAmount: asOdooDouble(json['final_agreed_amount']),
      discountPct: asOdooDouble(json['discount_pct']),
      financingType: asOdooString(json['financing_type'], 'cash'),
      state: asOdooString(json['state'], 'draft'),
      date: parseDate(json['date']),
      dateExpiry: parseDate(json['date_expiry']),
      notes: asOdooString(json['notes']),
    );
  }
}

class OfferStateStyle {
  static String label(String s) => switch (s) {
    'submitted' => 'Presentada',
    'countered' => 'Contraoferta',
    'accepted' => 'Aceptada',
    'rejected' => 'Rechazada',
    'expired' => 'Vencida',
    _ => 'Borrador',
  };

  static Color color(String s, AppPalette colors) => switch (s) {
    'submitted' => colors.info,
    'countered' => colors.warning,
    'accepted' => colors.success,
    'rejected' || 'expired' => colors.danger,
    _ => colors.mutedLight,
  };
}

class OfferFinancingStyle {
  static String label(String s) => switch (s) {
    'mortgage' => 'Hipotecario (BIESS/Banco)',
    'owner' => 'Financiamiento del vendedor',
    'other' => 'Otro',
    _ => 'Contado',
  };

  static const List<(String, String)> options = [
    ('cash', 'Contado'),
    ('mortgage', 'Hipotecario (BIESS/Banco)'),
    ('owner', 'Financiamiento del vendedor'),
    ('other', 'Otro'),
  ];
}
