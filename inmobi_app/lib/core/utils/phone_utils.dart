import 'package:flutter/material.dart';
import 'package:share_plus/share_plus.dart';
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

    // 1. En iOS/Android intentar primero el esquema nativo directo de WhatsApp.
    // 'whatsapp' está declarado en LSApplicationQueriesSchemes de iOS (Info.plist),
    // lo que abre WhatsApp al instante sin intermediación de Safari.
    final textParam = text != null && text.isNotEmpty
        ? '&text=${Uri.encodeComponent(text)}'
        : '';
    final nativeUri = Uri.parse('whatsapp://send?phone=$n$textParam');
    final openedNative = await _launch(
      nativeUri,
      mode: LaunchMode.externalApplication,
    );
    if (openedNative) return true;

    // 2. Fallback a enlace web/universal https://wa.me/
    final query = text != null && text.isNotEmpty
        ? '?text=${Uri.encodeComponent(text)}'
        : '';
    return _launch(
      Uri.parse('https://wa.me/$n$query'),
      mode: LaunchMode.externalApplication,
    );
  }

  /// Abre WhatsApp para compartir un texto con cualquier contacto o grupo.
  /// En iOS, 'whatsapp://send?text=...' abre la app y presenta el selector nativo
  /// de chats de WhatsApp. Si WhatsApp no está instalado, recurre al Share Sheet
  /// del sistema (con sharePositionOrigin para soporte completo en iPad/iOS).
  static Future<bool> shareWhatsapp(
    String text, {
    Rect? sharePositionOrigin,
    String? subject,
  }) async {
    if (text.isEmpty) return false;

    // 1. Intentar esquema nativo de WhatsApp
    final nativeUri = Uri.parse(
      'whatsapp://send?text=${Uri.encodeComponent(text)}',
    );
    final openedNative = await _launch(
      nativeUri,
      mode: LaunchMode.externalApplication,
    );
    if (openedNative) return true;

    // 2. Si no abre WhatsApp (p.ej. no está instalado), abrir Share Sheet nativo
    try {
      final res = await Share.share(
        text,
        subject: subject,
        sharePositionOrigin: sharePositionOrigin,
      );
      return res.status != ShareResultStatus.unavailable;
    } catch (_) {
      // 3. Último recurso: enlace web de WhatsApp
      final webUri = Uri.parse(
        'https://api.whatsapp.com/send?text=${Uri.encodeComponent(text)}',
      );
      return _launch(webUri, mode: LaunchMode.externalApplication);
    }
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
