import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

class PhoneUtils {
  PhoneUtils._();

  static const defaultCountryCode = '593';

  static const List<CountryCode> countryCodes = [
    CountryCode('593', '🇪🇨', 'Ecuador'),
    CountryCode('1', '🇺🇸', 'Estados Unidos / Canadá'),
    CountryCode('34', '🇪🇸', 'España'),
    CountryCode('57', '🇨🇴', 'Colombia'),
    CountryCode('51', '🇵🇪', 'Perú'),
    CountryCode('58', '🇻🇪', 'Venezuela'),
    CountryCode('52', '🇲🇽', 'México'),
    CountryCode('54', '🇦🇷', 'Argentina'),
    CountryCode('56', '🇨🇱', 'Chile'),
  ];

  /// Deja el número en dígitos con código de país: ya con este código se
  /// devuelve igual; con 0 inicial se cambia el 0 por el código; 11+ dígitos
  /// se asume que ya traen otro país; el resto se asume local.
  static String normalize(
    String raw, {
    String countryCode = defaultCountryCode,
  }) {
    final digits = raw.replaceAll(RegExp(r'[^0-9]'), '');
    if (digits.isEmpty) return '';

    if (digits.startsWith(countryCode) &&
        digits.length > countryCode.length + 6) {
      return digits;
    }

    if (digits.startsWith('0')) {
      return '$countryCode${digits.substring(1)}';
    }

    if (digits.length >= 11) {
      return digits;
    }

    return '$countryCode$digits';
  }

  static Future<bool> call(
    String raw, {
    String countryCode = defaultCountryCode,
  }) async {
    final n = normalize(raw, countryCode: countryCode);
    if (n.isEmpty) return false;
    return _launch(Uri.parse('tel:+$n'));
  }

  static Future<bool> whatsapp(
    String raw, {
    String countryCode = defaultCountryCode,
    String? text,
  }) async {
    final n = normalize(raw, countryCode: countryCode);
    if (n.isEmpty) return false;
    final query = text != null && text.isNotEmpty
        ? '?text=${Uri.encodeComponent(text)}'
        : '';
    return _launch(
      Uri.parse('https://wa.me/$n$query'),
      mode: LaunchMode.externalApplication,
    );
  }

  /// No usar canLaunchUrl antes: en iOS devuelve false para todo esquema no
  /// declarado en LSApplicationQueriesSchemes, y los botones quedan mudos.
  static Future<bool> _launch(Uri uri, {LaunchMode? mode}) async {
    try {
      return await launchUrl(uri, mode: mode ?? LaunchMode.platformDefault);
    } catch (_) {
      return false;
    }
  }
}

class CountryCode {
  final String dialCode;
  final String flag;
  final String name;
  const CountryCode(this.dialCode, this.flag, this.name);

  String get label => '$flag +$dialCode';
}

class CountryCodeDropdown extends StatelessWidget {
  final String value;
  final ValueChanged<String> onChanged;

  const CountryCodeDropdown({
    super.key,
    required this.value,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return DropdownButtonHideUnderline(
      child: DropdownButton<String>(
        value: value,
        isDense: true,
        items: PhoneUtils.countryCodes
            .map(
              (c) => DropdownMenuItem(value: c.dialCode, child: Text(c.label)),
            )
            .toList(),
        onChanged: (v) {
          if (v != null) onChanged(v);
        },
      ),
    );
  }
}
