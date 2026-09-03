import 'package:flutter/material.dart';

/// Sistema de movimiento de Inmobi.
///
/// Los resortes se describen con los dos parámetros que usa Apple en sus
/// interfaces (y no con masa/rigidez/amortiguación sueltas), porque son los
/// que se piensan al diseñar:
///
/// * **damping** — cuánto rebota. `1.0` llega y se queda quieto; por debajo
///   de `1.0` se pasa y regresa. Se reserva el rebote para gestos que traían
///   impulso (un swipe, un flick): rebotar en un menú que solo apareció se
///   siente falso.
/// * **response** — qué tan rápido alcanza el destino, en segundos. No es una
///   "duración": un resorte no tiene duración fija, se asienta solo.
class AppMotion {
  AppMotion._();

  // ── Resortes (para movimiento físico, interrumpible) ──

  /// Resorte por defecto: llega firme, sin rebote. Para indicadores que se
  /// desplazan, hojas que se acomodan, cualquier cosa que no venga de un gesto.
  static final SpringDescription spring = _describe(damping: 1.0, response: 0.35);

  /// Resorte con un poco de rebote — solo cuando el gesto traía impulso.
  static final SpringDescription springBouncy = _describe(damping: 0.8, response: 0.4);

  /// Resorte corto para micro-interacciones (presionar, soltar).
  static final SpringDescription springSnappy = _describe(damping: 1.0, response: 0.22);

  /// Convierte damping + response al `SpringDescription` de Flutter.
  /// ω₀ = 2π/response · k = ω₀²·m · c = 2·ζ·ω₀·m  (con masa = 1)
  static SpringDescription _describe({
    required double damping,
    required double response,
  }) {
    final omega = 2 * 3.141592653589793 / response;
    return SpringDescription(
      mass: 1,
      stiffness: omega * omega,
      damping: 2 * damping * omega,
    );
  }

  // ── Duraciones y curvas (para transiciones simples, no gestuales) ──

  /// Micro-feedback: color, opacidad, un ícono que cambia.
  static const fast = Duration(milliseconds: 160);

  /// El caballo de batalla: entradas, expansiones, cambios de estado.
  static const normal = Duration(milliseconds: 320);

  /// Movimientos grandes: una pantalla, una hoja que sube.
  static const slow = Duration(milliseconds: 460);

  /// Curva estándar — sale rápido y frena suave, sin pasarse.
  static const curve = Curves.easeOutCubic;

  /// Curva con un empujón extra al final, para elementos que "llegan".
  static const curveEmphasized = Curves.easeOutBack;

  /// Curva para salidas: arranca lento y acelera al irse.
  static const curveExit = Curves.easeInCubic;

  // ── Accesibilidad ──

  /// `true` cuando el sistema pide reducir movimiento. En ese caso las
  /// pantallas hacen un cross-fade corto en vez de desplazarse: se reduce el
  /// movimiento, no la retroalimentación.
  static bool reduced(BuildContext context) =>
      MediaQuery.maybeDisableAnimationsOf(context) ?? false;

  /// Duración que respeta la preferencia de movimiento reducido.
  static Duration duration(BuildContext context, Duration value) =>
      reduced(context) ? Duration.zero : value;

  /// Desplazamiento inicial de una entrada, anulado si se pide menos movimiento.
  static double offset(BuildContext context, double value) =>
      reduced(context) ? 0 : value;
}
