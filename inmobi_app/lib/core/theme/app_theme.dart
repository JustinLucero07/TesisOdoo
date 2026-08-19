import 'package:flutter/material.dart';

/// Paleta de marca REAL de Inmobi — navy #28235D + rojo #D81F26 del isotipo
/// de inmobi.com.ec, los mismos de las fichas PDF que genera el ERP.
///
/// Los colores se exponen por rol (fondo, superficie, texto, línea) y no por
/// valor fijo, para que la app pueda renderizarse en claro u oscuro sin
/// tocar ni una pantalla: cada widget pide `AppColors.of(context).surface`
/// y recibe el tono correcto según el tema activo.
class AppPalette {
  final bool isDark;

  // Marca
  final Color navy;
  final Color navyDeep;
  final Color navyLight;
  final Color accent;
  final Color accentSoft;

  // Superficies y texto
  final Color background;
  final Color surface;
  final Color surfaceAlt;
  final Color ink;
  final Color muted;
  final Color mutedLight;
  final Color line;

  // Semáforo
  final Color success;
  final Color successBg;
  final Color warning;
  final Color warningBg;
  final Color danger;
  final Color dangerBg;
  final Color info;
  final Color infoBg;
  final Color neutralBg;

  const AppPalette({
    required this.isDark,
    required this.navy,
    required this.navyDeep,
    required this.navyLight,
    required this.accent,
    required this.accentSoft,
    required this.background,
    required this.surface,
    required this.surfaceAlt,
    required this.ink,
    required this.muted,
    required this.mutedLight,
    required this.line,
    required this.success,
    required this.successBg,
    required this.warning,
    required this.warningBg,
    required this.danger,
    required this.dangerBg,
    required this.info,
    required this.infoBg,
    required this.neutralBg,
  });

  static const light = AppPalette(
    isDark: false,
    navy: Color(0xFF28235D),
    navyDeep: Color(0xFF1B1840),
    navyLight: Color(0xFF423B8C),
    accent: Color(0xFFD81F26),
    accentSoft: Color(0xFFFDECEC),
    background: Color(0xFFF7F6FB),
    surface: Colors.white,
    surfaceAlt: Color(0xFFF1EFF7),
    ink: Color(0xFF14112E),
    muted: Color(0xFF63607A),
    mutedLight: Color(0xFF9A97AB),
    line: Color(0xFFE4E1EE),
    success: Color(0xFF16A35A),
    successBg: Color(0xFFDFF7E9),
    warning: Color(0xFFE8871E),
    warningBg: Color(0xFFFFF1DB),
    danger: Color(0xFFE0292F),
    dangerBg: Color(0xFFFCE4E4),
    info: Color(0xFF0091EA),
    infoBg: Color(0xFFE1F3FF),
    neutralBg: Color(0xFFEFEDF5),
  );

  /// En oscuro el navy se aclara (sobre fondo oscuro el navy original es
  /// ilegible) y los semáforos suben luminosidad para mantener contraste.
  static const dark = AppPalette(
    isDark: true,
    navy: Color(0xFF9A92E0),
    navyDeep: Color(0xFF0E0C1E),
    navyLight: Color(0xFFB4ADEC),
    accent: Color(0xFFFF6B6F),
    accentSoft: Color(0xFF3A2028),
    background: Color(0xFF121027),
    surface: Color(0xFF1C1938),
    surfaceAlt: Color(0xFF242047),
    ink: Color(0xFFEDEBF7),
    muted: Color(0xFFA29FBA),
    mutedLight: Color(0xFF7D7A96),
    line: Color(0xFF322E56),
    success: Color(0xFF3DD68C),
    successBg: Color(0xFF14301F),
    warning: Color(0xFFFFB35C),
    warningBg: Color(0xFF35240F),
    danger: Color(0xFFFF6B6F),
    dangerBg: Color(0xFF3A1A1C),
    info: Color(0xFF4FB8F5),
    infoBg: Color(0xFF10283A),
    neutralBg: Color(0xFF262246),
  );
}

/// Acceso a la paleta desde cualquier widget: `AppColors.of(context)`.
/// Se mantiene además el acceso estático a la paleta clara para el código
/// que aún no recibe `context` (constantes en modelos de estilo).
class AppColors {
  AppColors._();

  static AppPalette of(BuildContext context) =>
      Theme.of(context).brightness == Brightness.dark
      ? AppPalette.dark
      : AppPalette.light;

  // Alias estáticos (tema claro) — se conservan para no romper el código
  // existente; las pantallas nuevas deben usar `AppColors.of(context)`.
  static const navy = Color(0xFF28235D);
  static const navyDeep = Color(0xFF1B1840);
  static const navyLight = Color(0xFF423B8C);
  static const accent = Color(0xFFD81F26);
  static const accentLight = Color(0xFFE85B60);
  static const ink = Color(0xFF14112E);
  static const muted = Color(0xFF63607A);
  static const mutedLight = Color(0xFF9A97AB);
  static const line = Color(0xFFE4E1EE);
  static const background = Color(0xFFF7F6FB);
  static const surface = Colors.white;
  static const success = Color(0xFF16A35A);
  static const successBg = Color(0xFFDFF7E9);
  static const warning = Color(0xFFE8871E);
  static const warningBg = Color(0xFFFFF1DB);
  static const danger = Color(0xFFE0292F);
  static const dangerBg = Color(0xFFFCE4E4);
  static const info = Color(0xFF0091EA);
  static const infoBg = Color(0xFFE1F3FF);
  static const neutralBg = Color(0xFFEFEDF5);
}

/// Escala tipográfica. Jost es una geométrica de proporciones amplias: a
/// tamaños grandes necesita tracking negativo para no leerse suelta, y a
/// tamaños chicos un poco de aire positivo para mantenerse legible.
class AppType {
  AppType._();

  static const family = 'Jost';

  static const display = TextStyle(
    fontSize: 28,
    fontWeight: FontWeight.w600,
    letterSpacing: -0.7,
    height: 1.15,
  );
  static const title = TextStyle(
    fontSize: 20,
    fontWeight: FontWeight.w600,
    letterSpacing: -0.4,
    height: 1.2,
  );
  static const heading = TextStyle(
    fontSize: 16,
    fontWeight: FontWeight.w600,
    letterSpacing: -0.2,
    height: 1.3,
  );
  static const body = TextStyle(fontSize: 14.5, height: 1.5, letterSpacing: 0);
  static const bodySmall = TextStyle(
    fontSize: 13,
    height: 1.45,
    letterSpacing: 0.1,
  );
  static const caption = TextStyle(
    fontSize: 11.5,
    height: 1.35,
    letterSpacing: 0.2,
  );
  static const label = TextStyle(
    fontSize: 10.5,
    fontWeight: FontWeight.w600,
    letterSpacing: 0.7,
    height: 1.2,
  );
  static const numeric = TextStyle(
    fontSize: 22,
    fontWeight: FontWeight.w600,
    letterSpacing: -0.5,
    height: 1,
  );
}

/// Escala de espaciado: múltiplos de 4, para que el ritmo vertical sea
/// consistente en toda la app en vez de números sueltos por pantalla.
class AppSpace {
  AppSpace._();
  static const xs = 4.0;
  static const sm = 8.0;
  static const md = 12.0;
  static const lg = 16.0;
  static const xl = 22.0;
  static const xxl = 30.0;
}

class AppRadius {
  AppRadius._();
  static const sm = 8.0;
  static const md = 12.0;
  static const lg = 16.0;
  static const pill = 100.0;
}

class AppTheme {
  AppTheme._();

  static ThemeData light() => _build(AppPalette.light);
  static ThemeData dark() => _build(AppPalette.dark);

  static ThemeData _build(AppPalette p) {
    final base = ThemeData(
      useMaterial3: true,
      brightness: p.isDark ? Brightness.dark : Brightness.light,
      fontFamily: AppType.family,
      colorScheme: ColorScheme.fromSeed(
        seedColor: p.navy,
        primary: p.navy,
        secondary: p.accent,
        surface: p.surface,
        brightness: p.isDark ? Brightness.dark : Brightness.light,
      ),
      scaffoldBackgroundColor: p.background,
      splashFactory: InkSparkle.splashFactory,
    );

    return base.copyWith(
      textTheme: base.textTheme
          .apply(
            fontFamily: AppType.family,
            bodyColor: p.ink,
            displayColor: p.ink,
          )
          .copyWith(
            headlineSmall: AppType.display.copyWith(color: p.ink),
            titleLarge: AppType.title.copyWith(color: p.ink),
            titleMedium: AppType.heading.copyWith(color: p.ink),
            bodyMedium: AppType.body.copyWith(color: p.ink),
            bodySmall: AppType.bodySmall.copyWith(color: p.muted),
            labelSmall: AppType.label.copyWith(color: p.mutedLight),
          ),
      appBarTheme: AppBarTheme(
        // Barra sobre el fondo, no un bloque navy sólido: deja que el
        // contenido sea el protagonista y el color de marca se reserve
        // para las acciones.
        backgroundColor: p.background,
        foregroundColor: p.ink,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        surfaceTintColor: Colors.transparent,
        titleTextStyle: AppType.title.copyWith(
          color: p.ink,
          fontFamily: AppType.family,
        ),
        iconTheme: IconThemeData(color: p.ink),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: p.navy,
          foregroundColor: p.isDark ? p.navyDeep : Colors.white,
          padding: const EdgeInsets.symmetric(vertical: 15, horizontal: 20),
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.md),
          ),
          textStyle: const TextStyle(
            fontWeight: FontWeight.w600,
            fontSize: 15,
            fontFamily: AppType.family,
            letterSpacing: 0.1,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: p.navy,
          side: BorderSide(color: p.line),
          padding: const EdgeInsets.symmetric(vertical: 13, horizontal: 18),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.md),
          ),
          textStyle: const TextStyle(
            fontWeight: FontWeight.w600,
            fontSize: 14,
            fontFamily: AppType.family,
          ),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: p.navy,
          textStyle: const TextStyle(
            fontWeight: FontWeight.w600,
            fontSize: 13.5,
            fontFamily: AppType.family,
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: p.surface,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: BorderSide(color: p.line),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: BorderSide(color: p.line),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: BorderSide(color: p.navy, width: 1.6),
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 14,
          vertical: 15,
        ),
        labelStyle: TextStyle(color: p.muted, fontFamily: AppType.family),
        hintStyle: TextStyle(color: p.mutedLight, fontFamily: AppType.family),
      ),
      cardTheme: CardThemeData(
        // Sin sombra pesada: la jerarquía la da el borde fino y el
        // contraste de superficie, que se lee limpio en ambos temas.
        elevation: 0,
        color: p.surface,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.lg),
          side: BorderSide(color: p.line),
        ),
      ),
      floatingActionButtonTheme: FloatingActionButtonThemeData(
        backgroundColor: p.accent,
        foregroundColor: Colors.white,
        elevation: 2,
        extendedTextStyle: const TextStyle(
          fontWeight: FontWeight.w600,
          fontSize: 14,
          fontFamily: AppType.family,
        ),
      ),
      chipTheme: base.chipTheme.copyWith(
        backgroundColor: p.neutralBg,
        labelStyle: TextStyle(
          fontSize: 12.5,
          fontWeight: FontWeight.w600,
          color: p.ink,
          fontFamily: AppType.family,
        ),
        side: BorderSide.none,
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.pill),
        ),
      ),
      dividerTheme: DividerThemeData(color: p.line, thickness: 1, space: 1),
      bottomNavigationBarTheme: BottomNavigationBarThemeData(
        selectedItemColor: p.navy,
        unselectedItemColor: p.mutedLight,
        backgroundColor: p.surface,
        elevation: 0,
        type: BottomNavigationBarType.fixed,
        selectedLabelStyle: const TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          fontFamily: AppType.family,
        ),
        unselectedLabelStyle: const TextStyle(
          fontSize: 11,
          fontFamily: AppType.family,
        ),
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: p.isDark ? p.surfaceAlt : p.navyDeep,
        contentTextStyle: const TextStyle(
          color: Colors.white,
          fontFamily: AppType.family,
          fontSize: 13.5,
        ),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
        ),
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: p.surface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.lg),
        ),
        titleTextStyle: AppType.heading.copyWith(
          color: p.ink,
          fontFamily: AppType.family,
        ),
        contentTextStyle: AppType.body.copyWith(
          color: p.muted,
          fontFamily: AppType.family,
        ),
      ),
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: p.surface,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        ),
      ),
      progressIndicatorTheme: ProgressIndicatorThemeData(
        color: p.navy,
        linearMinHeight: 3,
      ),
      listTileTheme: ListTileThemeData(
        titleTextStyle: AppType.body.copyWith(
          color: p.ink,
          fontFamily: AppType.family,
        ),
        subtitleTextStyle: AppType.caption.copyWith(
          color: p.muted,
          fontFamily: AppType.family,
        ),
      ),
    );
  }
}

/// Sombra suave para las piezas que deben despegarse del fondo (encabezado
/// del inicio, tarjetas destacadas). Se atenúa en oscuro, donde una sombra
/// negra sobre fondo oscuro no aporta separación.
List<BoxShadow> softShadow({double opacity = 0.06, bool isDark = false}) => [
  BoxShadow(
    color: Colors.black.withValues(alpha: isDark ? opacity * 2.2 : opacity),
    blurRadius: 18,
    offset: const Offset(0, 6),
  ),
];
