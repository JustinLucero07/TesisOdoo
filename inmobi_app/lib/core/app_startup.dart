import 'package:flutter/foundation.dart';

/// Avisos del arranque de la app.
class AppStartup {
  AppStartup._();

  /// El inicio (panel) ya trajo sus datos la primera vez: la pantalla de
  /// carga con el logo se queda hasta entonces, así no se ve una pantalla en
  /// blanco con un círculo después de la animación.
  static final ValueNotifier<bool> homeReady = ValueNotifier<bool>(false);
}
