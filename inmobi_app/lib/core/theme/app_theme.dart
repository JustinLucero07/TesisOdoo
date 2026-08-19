import 'package:flutter/material.dart';

/// Paleta de marca REAL de Inmobi — tomada de inmobi.com.ec (navy #28235D +
/// rojo #D81F26 del isotipo) y de las mismas fichas PDF que genera el ERP,
/// para que la app se sienta como parte del mismo sistema, no como algo
/// aparte con colores inventados.
class AppColors {
  AppColors._();

  static const navy = Color(0xFF28235D);
  static const navyDeep = Color(0xFF1B1840);
  static const navyLight = Color(0xFF423B8C);
  static const accent = Color(0xFFD81F26);
  static const accentLight = Color(0xFFE85B60);
  static const ink = Color(0xFF12141A);
  static const muted = Color(0xFF63666F);
  static const mutedLight = Color(0xFF9A9DA6);
  static const line = Color(0xFFE3E6EC);
  static const background = Color(0xFFF5F6F9);
  static const surface = Colors.white;

  // Estados / semáforo, reutilizados en badges de leads, visitas, propiedades.
  static const success = Color(0xFF1E8E5A);
  static const successBg = Color(0xFFE6F4ED);
  static const warning = Color(0xFFD8901F);
  static const warningBg = Color(0xFFFBF3E2);
  static const danger = Color(0xFFD64545);
  static const dangerBg = Color(0xFFFBEAEA);
  static const info = Color(0xFF00AEEF);
  static const infoBg = Color(0xFFEAF7FE);
  static const neutralBg = Color(0xFFF0F1F4);
}

class AppTheme {
  AppTheme._();

  static ThemeData light() {
    final base = ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: AppColors.navy,
        primary: AppColors.navy,
        secondary: AppColors.accent,
        brightness: Brightness.light,
      ),
      scaffoldBackgroundColor: AppColors.background,
      splashFactory: InkSparkle.splashFactory,
    );
    return base.copyWith(
      textTheme: base.textTheme.copyWith(
        headlineSmall: const TextStyle(
          fontWeight: FontWeight.w700,
          color: AppColors.ink,
          letterSpacing: -0.3,
        ),
        titleLarge: const TextStyle(
          fontWeight: FontWeight.w700,
          color: AppColors.ink,
        ),
        titleMedium: const TextStyle(
          fontWeight: FontWeight.w600,
          color: AppColors.ink,
        ),
        bodyMedium: const TextStyle(color: AppColors.ink, height: 1.4),
        bodySmall: const TextStyle(color: AppColors.muted, height: 1.35),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.navy,
        foregroundColor: Colors.white,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(
          color: Colors.white,
          fontSize: 19,
          fontWeight: FontWeight.w700,
        ),
        surfaceTintColor: Colors.transparent,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.navy,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 20),
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          textStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.surface,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.line),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.line),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.navy, width: 1.6),
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 14,
          vertical: 14,
        ),
        labelStyle: const TextStyle(color: AppColors.muted),
      ),
      cardTheme: CardThemeData(
        elevation: 3,
        shadowColor: AppColors.navy.withValues(alpha: 0.10),
        color: AppColors.surface,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: AppColors.line),
        ),
      ),
      floatingActionButtonTheme: const FloatingActionButtonThemeData(
        backgroundColor: AppColors.accent,
        foregroundColor: Colors.white,
        elevation: 3,
      ),
      chipTheme: base.chipTheme.copyWith(
        backgroundColor: AppColors.neutralBg,
        labelStyle: const TextStyle(
          fontSize: 12.5,
          fontWeight: FontWeight.w600,
          color: AppColors.ink,
        ),
        side: BorderSide.none,
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      ),
      dividerTheme: const DividerThemeData(
        color: AppColors.line,
        thickness: 1,
        space: 1,
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        selectedItemColor: AppColors.navy,
        unselectedItemColor: AppColors.mutedLight,
        backgroundColor: Colors.white,
        elevation: 8,
        type: BottomNavigationBarType.fixed,
        selectedLabelStyle: TextStyle(
          fontSize: 11.5,
          fontWeight: FontWeight.w600,
        ),
        unselectedLabelStyle: TextStyle(fontSize: 11.5),
      ),
    );
  }
}

/// Sombra suave y consistente para tarjetas "elevadas" (KPIs, hero cards) —
/// más presencia que el borde plano de [CardThemeData], para las piezas que
/// queremos que destaquen (dashboard, encabezados de detalle).
List<BoxShadow> softShadow({double opacity = 0.06}) => [
  BoxShadow(
    color: Colors.black.withValues(alpha: opacity),
    blurRadius: 18,
    offset: const Offset(0, 6),
  ),
];
