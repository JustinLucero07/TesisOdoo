import 'package:flutter/material.dart';

import '../../core/api/odoo_json.dart';
import '../../core/config.dart';
import '../../core/theme/app_theme.dart';

/// Espejo de `estate.property` — cubre los campos que un asesor necesita ver
/// y editar a diario desde el celular. No se mapean los campos de solo
/// backend (WordPress, IA/OCR, tramos financieros del cierre, etc.).
class Property {
  final int id;
  final String title;
  final String reference;
  final double price;
  final double bottomPrice;
  final double rentalPrice;
  final String offerType; // 'sale' | 'rent'
  final String state; // available | reserved | sold | rented | draft
  final String city;
  final String sector;
  final String street;
  final String streetNumber;
  final String zipCode;
  final String cadastralCode;
  final double area;
  final int bedrooms;
  final double bathrooms;
  final int parkingSpaces;
  final int floor;
  final int yearBuilt;
  final double commissionPercentage;
  final int? propertyTypeId;
  final String propertyTypeName;
  final String description;
  final bool isExclusive;
  final int? ownerId;
  final String ownerName;
  final int? buyerId;
  final String buyerName;
  final int? tenantId;
  final String tenantName;
  final int? userId;
  final String userName;
  final DateTime? dateListed;
  final int daysOnMarket;
  final double avmEstimatedPrice;
  final String avmStatus; // fair | high | low
  final List<int> imageIds;
  final bool wpPublished;
  final int wpPostId;
  final bool wpNeedsSync;
  final String captureSheetFilename;
  final bool hasCaptureSheet;

  Property({
    required this.id,
    required this.title,
    required this.reference,
    required this.price,
    this.bottomPrice = 0,
    required this.rentalPrice,
    required this.offerType,
    required this.state,
    required this.city,
    this.sector = '',
    this.street = '',
    this.streetNumber = '',
    this.zipCode = '',
    this.cadastralCode = '',
    required this.area,
    required this.bedrooms,
    required this.bathrooms,
    this.parkingSpaces = 0,
    this.floor = 0,
    this.yearBuilt = 0,
    this.commissionPercentage = 5.0,
    this.propertyTypeId,
    required this.propertyTypeName,
    this.description = '',
    this.isExclusive = false,
    this.ownerId,
    this.ownerName = '',
    this.buyerId,
    this.buyerName = '',
    this.tenantId,
    this.tenantName = '',
    this.userId,
    this.userName = '',
    this.dateListed,
    this.daysOnMarket = 0,
    this.avmEstimatedPrice = 0,
    this.avmStatus = '',
    this.imageIds = const [],
    this.wpPublished = false,
    this.wpPostId = 0,
    this.wpNeedsSync = false,
    this.captureSheetFilename = '',
    this.hasCaptureSheet = false,
  });

  bool get isForSale => offerType == 'sale';

  double get displayPrice => isForSale ? price : rentalPrice;

  String get wpUrl => wpPostId > 0 ? '${AppConfig.wordpressSite}/?p=$wpPostId' : '';

  // Ojo: `image_main` NO va aquí a propósito — traerla en search_read
  // significa que Odoo la manda como base64 embebida en el JSON del
  // listado completo (pesado con catálogos grandes). Las fotos se cargan
  // aparte, perezosamente y ya redimensionadas, con OdooImage.
  static const List<String> listFields = [
    'title',
    'name',
    'price',
    'rental_price',
    'offer_type',
    'state',
    'city',
    'sector',
    'area',
    'bedrooms',
    'bathrooms',
    'property_type_id',
    'is_exclusive',
    // Texto liviano (no imagen) — se trae también en el listado para poder
    // expandir la tarjeta y mostrar un resumen sin ida y vuelta al servidor.
    'description',
    // One2many — Odoo devuelve solo la lista de ids (liviano), no las
    // imágenes en sí. Con eso alcanza para armar el carrusel de la tarjeta.
    'image_ids',
  ];

  static const List<String> detailFields = [
    ...listFields,
    'street',
    'sector',
    'street_number',
    'zip_code',
    'cadastral_code',
    'bottom_price',
    'parking_spaces',
    'floor',
    'year_built',
    'commission_percentage',
    'is_exclusive',
    'owner_id',
    'buyer_id',
    'tenant_id',
    'user_id',
    'date_listed',
    'days_on_market',
    'avm_estimated_price',
    'avm_status',
    'wp_published',
    'wp_post_id',
    'wp_needs_sync',
    'capture_sheet_filename',
  ];

  factory Property.fromJson(Map<String, dynamic> json) {
    final captureFn = asOdooString(json['capture_sheet_filename']);
    return Property(
      id: json['id'] as int,
      title: asOdooString(json['title']),
      reference: asOdooString(json['name']),
      price: asOdooDouble(json['price']),
      bottomPrice: asOdooDouble(json['bottom_price']),
      rentalPrice: asOdooDouble(json['rental_price']),
      offerType: asOdooString(json['offer_type'], 'sale'),
      state: asOdooString(json['state'], 'available'),
      city: asOdooString(json['city']),
      sector: asOdooString(json['sector']),
      street: asOdooString(json['street']),
      streetNumber: asOdooString(json['street_number']),
      zipCode: asOdooString(json['zip_code']),
      cadastralCode: asOdooString(json['cadastral_code']),
      area: asOdooDouble(json['area']),
      bedrooms: asOdooInt(json['bedrooms']),
      bathrooms: asOdooDouble(json['bathrooms']),
      parkingSpaces: asOdooInt(json['parking_spaces']),
      floor: asOdooInt(json['floor']),
      yearBuilt: asOdooInt(json['year_built']),
      commissionPercentage: asOdooDouble(json['commission_percentage'], 5.0),
      propertyTypeId: json['property_type_id'] is List
          ? json['property_type_id'][0] as int
          : null,
      propertyTypeName: many2oneName(json['property_type_id']),
      // `description` es un campo Html en Odoo (viene con <p>/<ul>/etc.) —
      // se limpia a texto plano para mostrarlo simple en la app.
      description: asOdooString(json['description'])
          .replaceAll(RegExp(r'<[^>]*>'), ' ')
          .replaceAll(RegExp(r'\s+'), ' ')
          .trim(),
      isExclusive: json['is_exclusive'] == true,
      ownerId: json['owner_id'] is List ? json['owner_id'][0] as int : null,
      ownerName: many2oneName(json['owner_id']),
      buyerId: json['buyer_id'] is List ? json['buyer_id'][0] as int : null,
      buyerName: many2oneName(json['buyer_id']),
      tenantId: json['tenant_id'] is List ? json['tenant_id'][0] as int : null,
      tenantName: many2oneName(json['tenant_id']),
      userId: json['user_id'] is List ? json['user_id'][0] as int : null,
      userName: many2oneName(json['user_id']),
      dateListed: json['date_listed'] is String
          ? DateTime.tryParse(json['date_listed'])
          : null,
      daysOnMarket: asOdooInt(json['days_on_market']),
      avmEstimatedPrice: asOdooDouble(json['avm_estimated_price']),
      avmStatus: asOdooString(json['avm_status']),
      imageIds: json['image_ids'] is List
          ? (json['image_ids'] as List).cast<int>()
          : const [],
      wpPublished: json['wp_published'] == true,
      wpPostId: asOdooInt(json['wp_post_id']),
      wpNeedsSync: json['wp_needs_sync'] == true,
      captureSheetFilename: captureFn,
      hasCaptureSheet: captureFn.isNotEmpty || (json['capture_sheet'] != null && json['capture_sheet'] != false),
    );
  }
}

class PropertyStateLabel {
  static String label(String state) {
    switch (state) {
      case 'available':
        return 'Disponible';
      case 'reserved':
        return 'Reservada';
      case 'sold':
        return 'Vendida';
      case 'rented':
        return 'Arrendada';
      case 'draft':
        return 'Borrador';
      default:
        return state;
    }
  }

  static Color color(String state) => switch (state) {
    'available' => AppColors.success,
    'reserved' => AppColors.warning,
    'sold' || 'rented' => AppColors.navy,
    _ => AppColors.muted,
  };
}

class PropertyAvmStyle {
  static String label(String status) => switch (status) {
    'fair' => 'Precio justo',
    'high' => 'Sobre el mercado',
    'low' => 'Bajo el mercado',
    _ => 'Sin calcular',
  };

  static Color color(String status) => switch (status) {
    'fair' => AppColors.success,
    'high' => AppColors.danger,
    'low' => AppColors.warning,
    _ => AppColors.mutedLight,
  };
}
