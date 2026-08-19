import 'package:flutter/material.dart';

import '../../core/api/odoo_json.dart';
import '../../core/theme/app_theme.dart';

class Lead {
  final int id;
  final String name;
  final String contactName;
  final String phone;
  final String email;
  final double clientBudget;
  final int matchPercentage;
  final String leadScore; // low | medium | high
  final String leadTemperature; // cold | warm | hot | boiling
  final int? stageId;
  final String stageName;
  final int? targetPropertyId;
  final String targetPropertyName;
  final int? partnerId;
  final String partnerName;
  final String leadSourceName;
  final String clientNeeds;
  final String smartNegotiationTips;
  final int? preferredPropertyTypeId;
  final String preferredPropertyTypeName;
  final String preferredCity;
  final int preferredBedrooms;
  final double preferredMinArea;
  final double preferredMaxArea;
  final String description; // "Notes" de Odoo, campo Html
  final int priority; // 0-3 estrellas
  final DateTime? dateDeadline;
  final double expectedRevenue;
  final double expectedCommission;
  final bool isGoldenOpportunity;
  final String closingDifficulty;
  final int completedVisitsCount;
  final int lastActivityDays;
  final int leadVelocityDays;

  Lead({
    required this.id,
    required this.name,
    required this.contactName,
    required this.phone,
    required this.email,
    required this.clientBudget,
    required this.matchPercentage,
    required this.leadScore,
    required this.leadTemperature,
    this.stageId,
    required this.stageName,
    this.targetPropertyId,
    required this.targetPropertyName,
    this.partnerId,
    this.partnerName = '',
    this.leadSourceName = '',
    this.clientNeeds = '',
    this.smartNegotiationTips = '',
    this.preferredPropertyTypeId,
    this.preferredPropertyTypeName = '',
    this.preferredCity = '',
    this.preferredBedrooms = 0,
    this.preferredMinArea = 0,
    this.preferredMaxArea = 0,
    this.description = '',
    this.priority = 0,
    this.dateDeadline,
    this.expectedRevenue = 0,
    this.expectedCommission = 0,
    this.isGoldenOpportunity = false,
    this.closingDifficulty = '',
    this.completedVisitsCount = 0,
    this.lastActivityDays = 0,
    this.leadVelocityDays = 0,
  });

  static const List<String> listFields = [
    'name',
    'contact_name',
    'phone',
    'email_from',
    'client_budget',
    'match_percentage',
    'lead_score',
    'lead_temperature',
    'stage_id',
    'target_property_id',
  ];

  static const List<String> detailFields = [
    ...listFields,
    'partner_id',
    'lead_source_id',
    'client_needs',
    'smart_negotiation_tips',
    'preferred_property_type_id',
    'preferred_city',
    'preferred_bedrooms',
    'preferred_min_area',
    'preferred_max_area',
    // "Notes" del CRM nativo + seguimiento comercial
    'description',
    'priority',
    'date_deadline',
    'expected_revenue',
    'expected_commission',
    'is_golden_opportunity',
    'closing_difficulty',
    'completed_visits_count',
    'last_activity_days',
    'lead_velocity_days',
  ];

  factory Lead.fromJson(Map<String, dynamic> json) {
    return Lead(
      id: json['id'] as int,
      name: asOdooString(json['name']),
      contactName: asOdooString(json['contact_name']),
      phone: asOdooString(json['phone']),
      email: asOdooString(json['email_from']),
      clientBudget: asOdooDouble(json['client_budget']),
      matchPercentage: asOdooInt(json['match_percentage']),
      leadScore: asOdooString(json['lead_score']),
      leadTemperature: asOdooString(json['lead_temperature']),
      stageId: json['stage_id'] is List ? json['stage_id'][0] as int : null,
      stageName: many2oneName(json['stage_id']),
      targetPropertyId: json['target_property_id'] is List
          ? json['target_property_id'][0] as int
          : null,
      targetPropertyName: many2oneName(json['target_property_id']),
      partnerId: json['partner_id'] is List
          ? json['partner_id'][0] as int
          : null,
      partnerName: many2oneName(json['partner_id']),
      leadSourceName: many2oneName(json['lead_source_id']),
      clientNeeds: asOdooString(json['client_needs']),
      smartNegotiationTips: asOdooString(json['smart_negotiation_tips']),
      preferredPropertyTypeId: json['preferred_property_type_id'] is List
          ? json['preferred_property_type_id'][0] as int
          : null,
      preferredPropertyTypeName: many2oneName(
        json['preferred_property_type_id'],
      ),
      preferredCity: asOdooString(json['preferred_city']),
      preferredBedrooms: asOdooInt(json['preferred_bedrooms']),
      preferredMinArea: asOdooDouble(json['preferred_min_area']),
      preferredMaxArea: asOdooDouble(json['preferred_max_area']),
      // `description` es Html en Odoo: se limpia a texto plano para leerlo
      // cómodo en el celular (mismo criterio que la descripción de propiedad).
      description: asOdooString(json['description'])
          .replaceAll(RegExp(r'<br\s*/?>', caseSensitive: false), '\n')
          .replaceAll(RegExp(r'</p>', caseSensitive: false), '\n')
          .replaceAll(RegExp(r'<[^>]*>'), '')
          .replaceAll(RegExp(r'\n{3,}'), '\n\n')
          .trim(),
      priority: asOdooInt(json['priority']),
      dateDeadline: json['date_deadline'] is String
          ? DateTime.tryParse(json['date_deadline'])
          : null,
      expectedRevenue: asOdooDouble(json['expected_revenue']),
      expectedCommission: asOdooDouble(json['expected_commission']),
      isGoldenOpportunity: json['is_golden_opportunity'] == true,
      closingDifficulty: asOdooString(json['closing_difficulty']),
      completedVisitsCount: asOdooInt(json['completed_visits_count']),
      lastActivityDays: asOdooInt(json['last_activity_days']),
      leadVelocityDays: asOdooInt(json['lead_velocity_days']),
    );
  }
}

class LeadClosingDifficultyStyle {
  static String label(String value) => switch (value) {
    'easy' => 'Cierre fácil',
    'moderate' => 'Cierre moderado',
    'hard' => 'Cierre difícil',
    _ => '',
  };

  static Color color(String value) => switch (value) {
    'easy' => AppColors.success,
    'moderate' => AppColors.warning,
    'hard' => AppColors.danger,
    _ => AppColors.mutedLight,
  };
}

class LeadScoreStyle {
  static String label(String score) => switch (score) {
    'high' => 'A · Prioritario',
    'medium' => 'B · Cualificado',
    'low' => 'C · Básico',
    _ => '—',
  };

  static Color color(String score) => switch (score) {
    'high' => AppColors.success,
    'medium' => AppColors.info,
    _ => AppColors.muted,
  };
}

class LeadTemperatureStyle {
  static String label(String temp) => switch (temp) {
    'boiling' => '¡Hirviendo!',
    'hot' => 'Caliente',
    'warm' => 'Tibio',
    'cold' => 'Frío',
    _ => '—',
  };

  static Color color(String temp) => switch (temp) {
    'boiling' => AppColors.danger,
    'hot' => Colors.deepOrange,
    'warm' => AppColors.warning,
    _ => AppColors.info,
  };

  static IconData icon(String temp) => switch (temp) {
    'boiling' || 'hot' => Icons.local_fire_department,
    'warm' => Icons.wb_sunny_outlined,
    _ => Icons.ac_unit,
  };
}
