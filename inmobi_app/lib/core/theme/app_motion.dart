import 'package:flutter/material.dart';

class AppMotion {
  AppMotion._();

  static final SpringDescription spring = _describe(
    damping: 1.0,
    response: 0.35,
  );

  static final SpringDescription springBouncy = _describe(
    damping: 0.8,
    response: 0.4,
  );

  static final SpringDescription springSnappy = _describe(
    damping: 1.0,
    response: 0.22,
  );

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

  static const fast = Duration(milliseconds: 160);

  static const normal = Duration(milliseconds: 320);

  static const slow = Duration(milliseconds: 460);

  static const curve = Curves.easeOutCubic;

  static const curveEmphasized = Curves.easeOutBack;

  static const curveExit = Curves.easeInCubic;

  static bool reduced(BuildContext context) =>
      MediaQuery.maybeDisableAnimationsOf(context) ?? false;

  static Duration duration(BuildContext context, Duration value) =>
      reduced(context) ? Duration.zero : value;

  static double offset(BuildContext context, double value) =>
      reduced(context) ? 0 : value;
}
