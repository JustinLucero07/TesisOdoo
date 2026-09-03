import 'dart:ui';

import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

enum GlassLevel { thin, regular, thick }

class GlassSurface extends StatelessWidget {
  final Widget child;
  final GlassLevel level;
  final BorderRadius borderRadius;
  final EdgeInsetsGeometry? padding;

  final Color? tint;

  final bool edgeHighlight;

  const GlassSurface({
    super.key,
    required this.child,
    this.level = GlassLevel.regular,
    this.borderRadius = const BorderRadius.all(Radius.circular(20)),
    this.padding,
    this.tint,
    this.edgeHighlight = true,
  });

  static const ColorFilter _vibrancy = ColorFilter.matrix(<double>[
    1.3846,
    -0.2765,
    -0.0281,
    0,
    0,
    -0.0954,
    1.2035,
    -0.0281,
    0,
    0,
    -0.0954,
    -0.2765,
    1.3719,
    0,
    0,
    0,
    0,
    0,
    1,
    0,
  ]);

  double get _blur => switch (level) {
    GlassLevel.thin => 12,
    GlassLevel.regular => 20,
    GlassLevel.thick => 30,
  };

  double get _tintOpacity => switch (level) {
    GlassLevel.thin => 0.55,
    GlassLevel.regular => 0.68,
    GlassLevel.thick => 0.76,
  };

  List<BoxShadow> _shadow(bool isDark) => switch (level) {
    GlassLevel.thin => [
      BoxShadow(
        color: Colors.black.withValues(alpha: isDark ? 0.28 : 0.05),
        blurRadius: 10,
        offset: const Offset(0, 2),
      ),
    ],
    GlassLevel.regular => [
      BoxShadow(
        color: Colors.black.withValues(alpha: isDark ? 0.34 : 0.07),
        blurRadius: 20,
        offset: const Offset(0, 6),
        spreadRadius: -4,
      ),
    ],
    GlassLevel.thick => [
      BoxShadow(
        color: Colors.black.withValues(alpha: isDark ? 0.44 : 0.10),
        blurRadius: 32,
        offset: const Offset(0, 10),
        spreadRadius: -6,
      ),
    ],
  };

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.of(context);
    final isDark = colors.isDark;

    final solid = MediaQuery.highContrastOf(context);

    final fill = tint ?? colors.surface;
    final content = Padding(padding: padding ?? EdgeInsets.zero, child: child);

    if (solid) {
      return DecoratedBox(
        decoration: BoxDecoration(
          color: fill,
          borderRadius: borderRadius,
          border: Border.all(color: colors.line),
          boxShadow: _shadow(isDark),
        ),
        child: content,
      );
    }

    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: borderRadius,
        boxShadow: _shadow(isDark),
      ),
      child: ClipRRect(
        borderRadius: borderRadius,
        child: BackdropFilter(
          filter: ImageFilter.compose(
            outer: _vibrancy,
            inner: ImageFilter.blur(sigmaX: _blur, sigmaY: _blur),
          ),
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: fill.withValues(alpha: _tintOpacity),
              borderRadius: borderRadius,
              border: edgeHighlight
                  ? Border.all(
                      color: isDark
                          ? Colors.white.withValues(alpha: 0.14)
                          : Colors.white.withValues(alpha: 0.65),
                      width: 1,
                    )
                  : Border.all(color: colors.line.withValues(alpha: 0.6)),

              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Colors.white.withValues(alpha: isDark ? 0.06 : 0.30),
                  Colors.white.withValues(alpha: 0.0),
                ],
                stops: const [0.0, 0.45],
              ),
            ),
            child: content,
          ),
        ),
      ),
    );
  }
}

class GlassBar extends StatelessWidget {
  const GlassBar({super.key});

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.of(context);
    final solid = MediaQuery.highContrastOf(context);

    if (solid) {
      return ColoredBox(color: colors.surface);
    }

    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.compose(
          outer: GlassSurface._vibrancy,
          inner: ImageFilter.blur(sigmaX: 24, sigmaY: 24),
        ),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: colors.surface.withValues(alpha: 0.72),
            border: Border(
              bottom: BorderSide(color: colors.line.withValues(alpha: 0.7)),
            ),
          ),
        ),
      ),
    );
  }
}

class ScrollEdgeFade extends StatelessWidget {
  final double height;
  final Alignment begin;

  const ScrollEdgeFade({
    super.key,
    this.height = 90,
    this.begin = Alignment.bottomCenter,
  });

  @override
  Widget build(BuildContext context) {
    final bg = AppColors.of(context).background;
    return IgnorePointer(
      child: Container(
        height: height,
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: begin,
            end: begin == Alignment.bottomCenter
                ? Alignment.topCenter
                : Alignment.bottomCenter,
            colors: [bg, bg.withValues(alpha: 0.0)],
          ),
        ),
      ),
    );
  }
}
