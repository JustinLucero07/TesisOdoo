/// Helpers para leer valores de las respuestas JSON-RPC de Odoo.
///
/// Odoo devuelve `false` (no `null`) para casi cualquier campo vacío —
/// texto sin llenar, Many2one sin asignar, fecha sin definir, etc. El
/// operador `??` de Dart SOLO reacciona a `null`, así que un patrón como
/// `(json['x'] ?? '') as String` revienta con un error de tipo en cuanto
/// el campo real es `false` en vez de nulo. Estos helpers evitan ese bug
/// en todos los modelos, en un solo lugar.
library;

String asOdooString(dynamic v, [String fallback = '']) =>
    v is String ? v : fallback;

int asOdooInt(dynamic v, [int fallback = 0]) => v is num ? v.toInt() : fallback;

double asOdooDouble(dynamic v, [double fallback = 0]) =>
    v is num ? v.toDouble() : fallback;

/// Nombre legible de un campo Many2one — Odoo lo manda como `[id, "Nombre"]`,
/// o `false` si no está asignado.
String many2oneName(dynamic v) =>
    (v is List && v.length > 1) ? v[1].toString() : '';
