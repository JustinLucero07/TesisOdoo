import 'package:flutter/material.dart';

import '../../core/api/odoo_json.dart';
import '../../core/theme/app_theme.dart';

class EstateDocument {
  final int id;
  final String name;
  final String filename;
  final bool isPdf;
  final double fileSizeMb;
  final int? typeId;
  final String typeName;
  final String typeCategory;
  final String state;
  final String confidentiality;
  final DateTime? date;
  final DateTime? expirationDate;
  final int? propertyId;
  final String propertyName;
  final int? partnerId;
  final String partnerName;
  final int? contractId;
  final String contractName;
  final int? leadId;
  final String leadName;
  final String rejectionReason;
  final String verifiedByName;
  final DateTime? verifiedDate;

  EstateDocument({
    required this.id,
    required this.name,
    required this.filename,
    required this.isPdf,
    required this.fileSizeMb,
    this.typeId,
    required this.typeName,
    this.typeCategory = '',
    required this.state,
    this.confidentiality = 'internal',
    this.date,
    this.expirationDate,
    this.propertyId,
    this.propertyName = '',
    this.partnerId,
    this.partnerName = '',
    this.contractId,
    this.contractName = '',
    this.leadId,
    this.leadName = '',
    this.rejectionReason = '',
    this.verifiedByName = '',
    this.verifiedDate,
  });

  static const List<String> listFields = [
    'name',
    'filename',
    'is_pdf',
    'file_size',
    'type_id',
    'type_category',
    'state',
    'confidentiality',
    'date',
    'expiration_date',
    'property_id',
    'partner_id',
    'contract_id',
    'lead_id',
    'rejection_reason',
    'verified_by',
    'verified_date',
  ];

  factory EstateDocument.fromJson(Map<String, dynamic> json) {
    return EstateDocument(
      id: json['id'] as int,
      name: asOdooString(json['name']),
      filename: asOdooString(json['filename']),
      isPdf: json['is_pdf'] == true,
      fileSizeMb: asOdooDouble(json['file_size']),
      typeId: json['type_id'] is List ? json['type_id'][0] as int : null,
      typeName: many2oneName(json['type_id']),
      typeCategory: asOdooString(json['type_category']),
      state: asOdooString(json['state'], 'received'),
      confidentiality: asOdooString(json['confidentiality'], 'internal'),
      date: json['date'] is String ? DateTime.tryParse(json['date']) : null,
      expirationDate: json['expiration_date'] is String
          ? DateTime.tryParse(json['expiration_date'])
          : null,
      propertyId: json['property_id'] is List ? json['property_id'][0] as int : null,
      propertyName: many2oneName(json['property_id']),
      partnerId: json['partner_id'] is List ? json['partner_id'][0] as int : null,
      partnerName: many2oneName(json['partner_id']),
      contractId: json['contract_id'] is List ? json['contract_id'][0] as int : null,
      contractName: many2oneName(json['contract_id']),
      leadId: json['lead_id'] is List ? json['lead_id'][0] as int : null,
      leadName: many2oneName(json['lead_id']),
      rejectionReason: asOdooString(json['rejection_reason']),
      verifiedByName: many2oneName(json['verified_by']),
      verifiedDate: json['verified_date'] is String
          ? DateTime.tryParse(json['verified_date'])
          : null,
    );
  }

  IconData get icon {
    if (isPdf) return Icons.picture_as_pdf_outlined;
    final ext = filename.toLowerCase();
    if (ext.endsWith('.jpg') ||
        ext.endsWith('.jpeg') ||
        ext.endsWith('.png') ||
        ext.endsWith('.webp')) {
      return Icons.image_outlined;
    }
    if (ext.endsWith('.doc') || ext.endsWith('.docx')) {
      return Icons.description_outlined;
    }
    if (ext.endsWith('.xls') || ext.endsWith('.xlsx')) {
      return Icons.table_chart_outlined;
    }
    return Icons.insert_drive_file_outlined;
  }
}

class DocumentStateStyle {
  static String label(String state) => switch (state) {
    'pending' => 'Pendiente',
    'verified' => 'Verificado',
    'rejected' => 'Rechazado',
    'archived' => 'Archivado',
    _ => 'Recibido',
  };

  static Color color(String state, AppPalette colors) => switch (state) {
    'pending' => colors.warning,
    'verified' => colors.success,
    'rejected' => colors.danger,
    'archived' => colors.mutedLight,
    _ => colors.info,
  };
}

class DocumentConfidentialityStyle {
  static String label(String level) => switch (level) {
    'public' => 'Público',
    'restricted' => 'Restringido',
    'confidential' => 'Confidencial',
    _ => 'Interno',
  };

  static Color color(String level, AppPalette colors) => switch (level) {
    'public' => colors.success,
    'restricted' => colors.warning,
    'confidential' => colors.danger,
    _ => colors.muted,
  };
}
