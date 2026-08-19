import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Preferencia de tema del usuario (sistema / claro / oscuro), persistida en
/// el dispositivo para que se respete entre aperturas de la app.
class ThemeController extends ChangeNotifier {
  static const _key = 'inmobi_theme_mode';
  final _storage = const FlutterSecureStorage();

  ThemeMode _mode = ThemeMode.system;
  ThemeMode get mode => _mode;

  Future<void> load() async {
    try {
      final saved = await _storage.read(key: _key);
      if (saved == null) return;
      _mode = switch (saved) {
        'light' => ThemeMode.light,
        'dark' => ThemeMode.dark,
        _ => ThemeMode.system,
      };
      notifyListeners();
    } catch (_) {
      // Sin almacenamiento seguro disponible se queda en "sistema".
    }
  }

  Future<void> setMode(ThemeMode mode) async {
    _mode = mode;
    notifyListeners();
    try {
      await _storage.write(
        key: _key,
        value: switch (mode) {
          ThemeMode.light => 'light',
          ThemeMode.dark => 'dark',
          ThemeMode.system => 'system',
        },
      );
    } catch (_) {
      // La preferencia sigue aplicada en memoria aunque no se persista.
    }
  }

  String get label => switch (_mode) {
    ThemeMode.light => 'Claro',
    ThemeMode.dark => 'Oscuro',
    ThemeMode.system => 'Según el sistema',
  };
}
