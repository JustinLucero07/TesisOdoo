library;

String asOdooString(dynamic v, [String fallback = '']) =>
    v is String ? v : fallback;

int asOdooInt(dynamic v, [int fallback = 0]) => v is num ? v.toInt() : fallback;

double asOdooDouble(dynamic v, [double fallback = 0]) =>
    v is num ? v.toDouble() : fallback;

String many2oneName(dynamic v) =>
    (v is List && v.length > 1) ? v[1].toString() : '';

/// Primer teléfono disponible de un contacto (phone, si no mobile).
String partnerPhone(Map<String, dynamic> row) {
  final phone = asOdooString(row['phone']);
  return phone.isNotEmpty ? phone : asOdooString(row['mobile']);
}
