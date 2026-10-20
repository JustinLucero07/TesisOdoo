import 'dart:convert';
import 'dart:io';

import 'package:path_provider/path_provider.dart';

/// Guarda en el celular la última respuesta de cada consulta de lectura a
/// Odoo, para poder mostrarla cuando no hay conexión (visitas con mala señal).
class OfflineCache {
  OfflineCache._();

  static Directory? _dir;

  static Future<Directory> _folder() async {
    if (_dir != null) return _dir!;
    final base = await getApplicationSupportDirectory();
    final dir = Directory('${base.path}/odoo_cache');
    if (!await dir.exists()) await dir.create(recursive: true);
    return _dir = dir;
  }

  /// Hash FNV-1a de 64 bits: nombre de archivo corto y estable para la clave.
  static String _hash(String key) {
    var h = 0xcbf29ce484222325;
    for (final c in utf8.encode(key)) {
      h ^= c;
      h = (h * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF;
    }
    return h.toUnsigned(64).toRadixString(16);
  }

  static Future<File> _file(String key) async =>
      File('${(await _folder()).path}/${_hash(key)}.json');

  static Future<void> write(String key, dynamic value) async {
    try {
      await (await _file(key)).writeAsString(jsonEncode(value), flush: false);
    } catch (_) {
      // El caché es un extra: si no se puede guardar, la app sigue igual.
    }
  }

  static Future<dynamic> read(String key) async {
    try {
      final file = await _file(key);
      if (!await file.exists()) return null;
      return jsonDecode(await file.readAsString());
    } catch (_) {
      return null;
    }
  }

  /// Al cerrar sesión no deben quedar datos de otro usuario.
  static Future<void> clear() async {
    try {
      final dir = await _folder();
      if (await dir.exists()) await dir.delete(recursive: true);
      _dir = null;
    } catch (_) {}
  }
}
