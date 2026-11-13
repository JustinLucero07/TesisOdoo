import 'package:intl/intl.dart';

import 'phone_utils.dart';

/// Formatos de números para toda la app, como se escriben en Ecuador.
class Fmt {
  Fmt._();

  /// "$135.000" (símbolo adelante; el formato es_EC lo ponía atrás).
  static NumberFormat money({int decimals = 0}) => NumberFormat.currency(
    locale: 'es_EC',
    symbol: r'$',
    decimalDigits: decimals,
    customPattern: decimals > 0 ? '¤#,##0.00' : '¤#,##0',
  );

  /// "5%" o "2,5%": sin decimales de sobra y con coma decimal.
  static String percent(double value) {
    final rounded = (value * 10).round() / 10;
    final text = rounded == rounded.roundToDouble()
        ? rounded.toStringAsFixed(0)
        : rounded.toStringAsFixed(1).replaceAll('.', ',');
    return '$text%';
  }

  /// "+593 98 593 0603" a partir de lo que esté guardado ("0985930603",
  /// "5930985930603"...). Si no se reconoce, se devuelve tal cual.
  static String phone(String raw) {
    if (raw.trim().isEmpty) return raw;
    var digits = PhoneUtils.normalize(raw);
    // "593" + "0" + número: el 0 de larga distancia sobra después del código.
    if (digits.startsWith('5930')) digits = '593${digits.substring(4)}';
    if (digits.startsWith('593') && digits.length == 12) {
      final n = digits.substring(3);
      return '+593 ${n.substring(0, 2)} ${n.substring(2, 5)} ${n.substring(5)}';
    }
    if (digits.startsWith('593') && digits.length == 11) {
      final n = digits.substring(3);
      return '+593 ${n.substring(0, 1)} ${n.substring(1, 4)} ${n.substring(4)}';
    }
    return raw;
  }
}
