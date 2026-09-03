import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

/// Normaliza teléfonos y abre llamada/WhatsApp de forma consistente en
/// toda la app.
///
/// El problema que resuelve: Odoo guarda los teléfonos como los escribió
/// quien los cargó — a veces en formato local ecuatoriano (0994998893),
/// a veces ya con código de país. Cada pantalla armaba el link de
/// llamar/WhatsApp a su manera (algunas solo quitaban espacios, ninguna
/// agregaba el código de país) — por eso WhatsApp decía "falta código de
/// país" y el marcador mostraba números truncados.
class PhoneUtils {
  PhoneUtils._();

  /// Ecuador es el mercado de la app: si un número no trae código de país
  /// explícito, se asume que es local ecuatoriano.
  static const defaultCountryCode = '593';

  /// Códigos de país para el selector de los formularios — no es una lista
  /// exhaustiva de todo el mundo, son los mercados reales de la
  /// inmobiliaria (Ecuador y los países de donde vienen más compradores/
  /// aliados). Ecuador va primero porque es el caso por defecto.
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

  /// Deja el número en dígitos puros con código de país, sin '+', sin
  /// espacios ni guiones — listo para `tel:` o `wa.me`.
  static String normalize(String raw, {String countryCode = defaultCountryCode}) {
    final digits = raw.replaceAll(RegExp(r'[^0-9]'), '');
    if (digits.isEmpty) return '';

    // Ya trae ESTE código de país explícito (ej. ya guardado como
    // 593994998893) — se deja tal cual, sin duplicar el prefijo.
    if (digits.startsWith(countryCode) && digits.length > countryCode.length + 6) {
      return digits;
    }

    // Formato local ecuatoriano con el 0 de troncal: 0994998893 -> quitar
    // el 0 y anteponer el código de país.
    if (digits.startsWith('0')) {
      return '$countryCode${digits.substring(1)}';
    }

    // 11+ dígitos sin el 0 inicial: probablemente ya trae OTRO código de
    // país (ej. un contacto de España cargado como 34612345678).
    if (digits.length >= 11) {
      return digits;
    }

    // Número corto sin 0 ni código de país reconocible: se asume local.
    return '$countryCode$digits';
  }

  /// Abre el marcador del teléfono con el número ya normalizado.
  static Future<bool> call(String raw, {String countryCode = defaultCountryCode}) async {
    final n = normalize(raw, countryCode: countryCode);
    if (n.isEmpty) return false;
    return _launch(Uri.parse('tel:+$n'));
  }

  /// Abre WhatsApp (con texto opcional) al número ya normalizado.
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

  /// Lanza el enlace directamente, sin consultar antes con `canLaunchUrl`.
  ///
  /// En iOS `canLaunchUrl` devuelve `false` para cualquier esquema que no
  /// esté declarado en `LSApplicationQueriesSchemes` del Info.plist — y
  /// como el código anterior estaba condicionado a esa consulta, tocar
  /// llamar/WhatsApp no hacía absolutamente nada, en silencio. La propia
  /// documentación de url_launcher recomienda intentar abrir y manejar el
  /// fallo, en vez de preguntar primero.
  static Future<bool> _launch(Uri uri, {LaunchMode? mode}) async {
    try {
      return await launchUrl(uri, mode: mode ?? LaunchMode.platformDefault);
    } catch (e) {
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

/// Selector de código de país compacto para anteponer a un campo de
/// teléfono en un formulario — así un asesor puede cargar un contacto de
/// España o Estados Unidos sin que el número quede mal interpretado como
/// ecuatoriano.
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
            .map((c) => DropdownMenuItem(value: c.dialCode, child: Text(c.label)))
            .toList(),
        onChanged: (v) {
          if (v != null) onChanged(v);
        },
      ),
    );
  }
}
