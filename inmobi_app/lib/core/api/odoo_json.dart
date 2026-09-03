library;

String asOdooString(dynamic v, [String fallback = '']) =>
    v is String ? v : fallback;

int asOdooInt(dynamic v, [int fallback = 0]) => v is num ? v.toInt() : fallback;

double asOdooDouble(dynamic v, [double fallback = 0]) =>
    v is num ? v.toDouble() : fallback;

String many2oneName(dynamic v) =>
    (v is List && v.length > 1) ? v[1].toString() : '';
