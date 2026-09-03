import 'package:flutter/material.dart';

import '../../core/api/odoo_json.dart';
import '../../core/theme/app_theme.dart';

/// Espejo de `res.partner` con los campos inmobiliarios que agrega
/// `estate_management` (propietario, agencia aliada, documento, etc.).
class Contact {
  final int id;
  final String name;
  final String phone;
  final String mobile;
  final String email;
  final String city;
  final String street;
  final String vat;
  final String idNumber;
  final String idType;
  final String profession;
  final bool isCompany;
  final bool isPropertyOwner;
  final bool isAlliedAgency;
  final int propertyOwnedCount;
  final int propertyBoughtCount;
  final int contractCount;
  final String preferredContact;
  final String function;

  Contact({
    required this.id,
    required this.name,
    this.phone = '',
    this.mobile = '',
    this.email = '',
    this.city = '',
    this.street = '',
    this.vat = '',
    this.idNumber = '',
    this.idType = '',
    this.profession = '',
    this.isCompany = false,
    this.isPropertyOwner = false,
    this.isAlliedAgency = false,
    this.propertyOwnedCount = 0,
    this.propertyBoughtCount = 0,
    this.contractCount = 0,
    this.preferredContact = '',
    this.function = '',
  });

  /// Número preferido para llamar/WhatsApp: el celular manda sobre el fijo.
  String get bestPhone => mobile.isNotEmpty ? mobile : phone;

  /// Etiqueta corta del rol, para el subtítulo de la lista.
  String get roleLabel {
    if (isAlliedAgency) return 'Agencia aliada';
    if (isPropertyOwner) return 'Propietario';
    if (isCompany) return 'Empresa';
    return 'Cliente';
  }

  Color roleColor(AppPalette colors) {
    if (isAlliedAgency) return colors.warning;
    if (isPropertyOwner) return colors.navy;
    if (isCompany) return colors.info;
    return colors.muted;
  }

  static const List<String> listFields = [
    'name',
    'phone',
    'mobile',
    'email',
    'city',
    'is_company',
    'is_property_owner',
    'is_allied_agency',
  ];

  static const List<String> detailFields = [
    ...listFields,
    'street',
    'vat',
    'id_number',
    'id_type',
    'profession',
    'function',
    'preferred_contact',
    'property_owned_count',
    'property_bought_count',
    'contract_count',
  ];

  factory Contact.fromJson(Map<String, dynamic> json) {
    return Contact(
      id: json['id'] as int,
      name: asOdooString(json['name']),
      phone: asOdooString(json['phone']),
      mobile: asOdooString(json['mobile']),
      email: asOdooString(json['email']),
      city: asOdooString(json['city']),
      street: asOdooString(json['street']),
      vat: asOdooString(json['vat']),
      idNumber: asOdooString(json['id_number']),
      idType: asOdooString(json['id_type']),
      profession: asOdooString(json['profession']),
      function: asOdooString(json['function']),
      isCompany: json['is_company'] == true,
      isPropertyOwner: json['is_property_owner'] == true,
      isAlliedAgency: json['is_allied_agency'] == true,
      propertyOwnedCount: asOdooInt(json['property_owned_count']),
      propertyBoughtCount: asOdooInt(json['property_bought_count']),
      contractCount: asOdooInt(json['contract_count']),
      preferredContact: asOdooString(json['preferred_contact']),
    );
  }
}

class ContactIdTypeStyle {
  static String label(String type) => switch (type) {
    'cedula' => 'Cédula de Identidad',
    'ruc' => 'RUC',
    'passport' => 'Pasaporte',
    'other' => 'Otro',
    _ => 'Documento',
  };

  static const List<(String, String)> options = [
    ('cedula', 'Cédula de Identidad'),
    ('ruc', 'RUC'),
    ('passport', 'Pasaporte'),
    ('other', 'Otro'),
  ];
}

class ContactPreferredContactStyle {
  static String label(String value) => switch (value) {
    'phone' => 'Llamada telefónica',
    'whatsapp' => 'WhatsApp',
    'email' => 'Correo electrónico',
    'any' => 'Cualquier canal',
    _ => '',
  };

  static const List<(String, String)> options = [
    ('phone', 'Llamada telefónica'),
    ('whatsapp', 'WhatsApp'),
    ('email', 'Correo electrónico'),
    ('any', 'Cualquier canal'),
  ];
}
