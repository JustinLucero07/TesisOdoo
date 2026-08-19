import 'package:flutter/material.dart';

import '../../core/api/odoo_json.dart';
import '../../core/theme/app_theme.dart';

class EstateDocument {
  final int id;
  final String name;
  final String filename;
  final bool isPdf;
  final double fileSizeMb;
  final String typeName;
  final String state;
  final DateTime? date;

  EstateDocument({
    required this.id,
    required this.name,
    required this.filename,
    required this.isPdf,
    required this.fileSizeMb,
    required this.typeName,
    required this.state,
    this.date,
  });

  static const List<String> listFields = [
    'name',
    'filename',
    'is_pdf',
    'file_size',
    'type_id',
    'state',
    'date',
  ];

  factory EstateDocument.fromJson(Map<String, dynamic> json) {
    return EstateDocument(
      id: json['id'] as int,
      name: asOdooString(json['name']),
      filename: asOdooString(json['filename']),
      isPdf: json['is_pdf'] == true,
      fileSizeMb: asOdooDouble(json['file_size']),
      typeName: many2oneName(json['type_id']),
      state: asOdooString(json['state'], 'received'),
      date: json['date'] is String ? DateTime.tryParse(json['date']) : null,
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
    if (ext.endsWith('.doc') || ext.endsWith('.docx'))
      return Icons.description_outlined;
    if (ext.endsWith('.xls') || ext.endsWith('.xlsx'))
      return Icons.table_chart_outlined;
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

  static Color color(String state) => switch (state) {
    'pending' => AppColors.warning,
    'verified' => AppColors.success,
    'rejected' => AppColors.danger,
    'archived' => AppColors.mutedLight,
    _ => AppColors.info,
  };
}
