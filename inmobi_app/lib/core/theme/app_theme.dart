import 'package:flutter/cupertino.dart' show CupertinoPageTransitionsBuilder;
import 'package:flutter/material.dart';

class AppPalette {
  final bool isDark;

  final Color navy;
  final Color navyDeep;
  final Color navyLight;
  final Color accent;
  final Color accentSoft;

  final Color background;
  final Color surface;
  final Color surfaceAlt;
  final Color ink;
  final Color muted;
  final Color mutedLight;
  final Color line;

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

  // Paleta oficial del logo Inmobi: azul marino #142559 (principal), azul
  // oscuro #0D1940, rojos #D9042B / #A60F2B y vino #590C37.
  static const light = AppPalette(
    isDark: false,
    navy: AppColors.navy,
    navyDeep: AppColors.navyDeep,
    navyLight: AppColors.navyLight,
    accent: AppColors.accent,
    accentSoft: Color(0xFFFDE6EA),
    background: Color(0xFFF6F8FC),
    surface: Colors.white,
    surfaceAlt: Color(0xFFEFF3FA),
    ink: Color(0xFF0E1630),
    muted: Color(0xFF5D6B85),
    mutedLight: Color(0xFF94A0B8),
    line: Color(0xFFE1E7F1),
    success: Color(0xFF10B981),
    successBg: Color(0xFFECFDF5),
    warning: Color(0xFFF59E0B),
    warningBg: Color(0xFFFFFBEB),
    danger: AppColors.accent,
    dangerBg: Color(0xFFFEF2F4),
    info: Color(0xFF0284C7),
    infoBg: Color(0xFFF0F9FF),
    neutralBg: Color(0xFFEFF3FA),
  );

  // Modo oscuro con los mismos azules de la marca (antes era violeta).
  static const dark = AppPalette(
    isDark: true,
    navy: AppColors.darkNavy,
    navyDeep: AppColors.navy,
    navyLight: Color(0xFFB4C4F7),
    accent: AppColors.accentLight,
    accentSoft: Color(0xFF3D0A16),
    background: AppColors.darkBackground,
    surface: AppColors.darkSurface,
    surfaceAlt: Color(0xFF17213F),
    ink: Color(0xFFF4F6FB),
    muted: Color(0xFF9AA6BF),
    mutedLight: Color(0xFF66738F),
    line: AppColors.darkLine,
    success: Color(0xFF34D399),
    successBg: Color(0xFF064E3B),
    warning: Color(0xFFFBBF24),
    warningBg: Color(0xFF451A03),
    danger: Color(0xFFFF6B81),
    dangerBg: Color(0xFF3D0A16),
    info: Color(0xFF38BDF8),
    infoBg: Color(0xFF0C4A6E),
    neutralBg: Color(0xFF141D38),
  );
}

class AppColors {
  AppColors._();

  static AppPalette of(BuildContext context) =>
      Theme.of(context).brightness == Brightness.dark
      ? AppPalette.dark
      : AppPalette.light;

  // Marca (logo)
  static const navy = Color(0xFF142559);
  static const navyDeep = Color(0xFF0D1940);
  static const navyLight = Color(0xFF2B418C);
  static const accent = Color(0xFFD9042B);
  static const accentDark = Color(0xFFA60F2B);
  static const wine = Color(0xFF590C37);
  static const accentLight = Color(0xFFFF4D6A);

  // Superficies del modo oscuro
  static const darkNavy = Color(0xFF8EA6F2);
  static const darkBackground = Color(0xFF070C1C);
  static const darkSurface = Color(0xFF0F1730);
  static const darkCard = Color(0xFF121B36);
  static const darkLine = Color(0xFF223056);

  static const ink = Color(0xFF0E1630);
  static const muted = Color(0xFF5D6B85);
  static const mutedLight = Color(0xFF94A0B8);
  static const line = Color(0xFFE1E7F1);
  static const background = Color(0xFFF6F8FC);
  static const surface = Colors.white;
  static const success = Color(0xFF10B981);
  static const successBg = Color(0xFFECFDF5);
  static const warning = Color(0xFFF59E0B);
  static const warningBg = Color(0xFFFFFBEB);
  static const danger = accent;
  static const dangerBg = Color(0xFFFEF2F4);
  static const info = Color(0xFF0284C7);
  static const infoBg = Color(0xFFF0F9FF);
  static const neutralBg = Color(0xFFEFF3FA);
  static const whatsapp = Color(0xFF25D366);
}

class AppType {
  AppType._();

  static const family = 'Jost';

  static const display = TextStyle(
    fontFamily: family,
    fontSize: 28,
    fontWeight: FontWeight.w600,
    letterSpacing: -0.7,
    height: 1.15,
  );
  static const title = TextStyle(
    fontFamily: family,
    fontSize: 20,
    fontWeight: FontWeight.w600,
    letterSpacing: -0.4,
    height: 1.2,
  );
  static const heading = TextStyle(
    fontFamily: family,
    fontSize: 16,
    fontWeight: FontWeight.w600,
    letterSpacing: -0.2,
    height: 1.3,
  );
  static const body = TextStyle(
    fontFamily: family,fontSize: 14.5, height: 1.5, letterSpacing: 0);
  static const bodySmall = TextStyle(
    fontFamily: family,
    fontSize: 13,
    height: 1.45,
    letterSpacing: 0.1,
  );
  static const caption = TextStyle(
    fontFamily: family,
    fontSize: 11.5,
    height: 1.35,
    letterSpacing: 0.2,
  );
  static const label = TextStyle(
    fontFamily: family,
    fontSize: 10.5,
    fontWeight: FontWeight.w600,
    letterSpacing: 0.7,
    height: 1.2,
  );
  static const numeric = TextStyle(
    fontFamily: family,
    fontSize: 22,
    fontWeight: FontWeight.w600,
    letterSpacing: -0.5,
    height: 1,
  );
}

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

      // iOS/macOS deben usar Cupertino: es el único builder que trae el gesto
      // de deslizar desde el borde para retroceder.
      pageTransitionsTheme: const PageTransitionsTheme(
        builders: {
          TargetPlatform.android: ZoomPageTransitionsBuilder(),
          TargetPlatform.iOS: CupertinoPageTransitionsBuilder(),
          TargetPlatform.linux: ZoomPageTransitionsBuilder(),
          TargetPlatform.macOS: CupertinoPageTransitionsBuilder(),
          TargetPlatform.windows: ZoomPageTransitionsBuilder(),
        },
      ),
    );
  }
}

List<BoxShadow> softShadow({double opacity = 0.04, bool isDark = false}) => [
  BoxShadow(
    color: Colors.black.withValues(
      alpha: isDark ? (opacity * 3).clamp(0.0, 0.25) : opacity,
    ),
    blurRadius: 10,
    offset: const Offset(0, 3),
  ),
];

List<BoxShadow> modernAmbientShadow({
  Color color = AppColors.navy,
  double opacity = 0.07,
  double blur = 24,
  Offset offset = const Offset(0, 8),
}) => [
  BoxShadow(
    color: color.withValues(alpha: opacity),
    blurRadius: blur,
    offset: offset,
    spreadRadius: -3,
  ),
];

class AppGlass {
  AppGlass._();

  static BoxDecoration decoration({
    required bool isDark,
    double opacity = 0.85,
    double radius = 20,
    Color? customColor,
    Border? border,
  }) {
    return BoxDecoration(
      color:
          customColor ??
          (isDark
              ? AppColors.darkSurface.withValues(alpha: opacity)
              : Colors.white.withValues(alpha: opacity)),
      borderRadius: BorderRadius.circular(radius),
      border:
          border ??
          Border.all(
            color: isDark
                ? Colors.white.withValues(alpha: 0.12)
                : const Color(0xFFE4E1EE).withValues(alpha: 0.9),
            width: 1,
          ),
      boxShadow: softShadow(opacity: isDark ? 0.25 : 0.06, isDark: isDark),
    );
  }
}

class AppGradients {
  AppGradients._();

  static const LinearGradient navyHero = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [AppColors.navy, AppColors.navyDeep],
  );

  static const LinearGradient accentHero = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFFE52D34), Color(0xFFB8151B)],
  );

  static const LinearGradient cardOverlay = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [Colors.transparent, Color(0xCC14112E)],
  );

  static const LinearGradient badgeGlass = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xDDFFFFFF), Color(0xAAFFFFFF)],
  );

  static const LinearGradient badgeGlassDark = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xDD1E1A3E), Color(0xAA1E1A3E)],
  );
}

class AppFeedback {
  AppFeedback._();

  static void light() {
    try {} catch (_) {}
  }

  static void selection() {
    try {} catch (_) {}
  }
}

class AppBreakpoints {
  AppBreakpoints._();

  static const double mobileMax = 600;
  static const double tabletMax = 960;

  static bool isMobile(BuildContext context) =>
      MediaQuery.sizeOf(context).width < mobileMax;

  static bool isTablet(BuildContext context) {
    final w = MediaQuery.sizeOf(context).width;
    return w >= mobileMax && w < tabletMax;
  }

  static bool isDesktop(BuildContext context) =>
      MediaQuery.sizeOf(context).width >= tabletMax;

  static int gridColumns(BuildContext context) {
    final w = MediaQuery.sizeOf(context).width;
    if (w >= tabletMax) return 3;
    if (w >= mobileMax) return 2;
    return 1;
  }
}
