import 'package:flutter/material.dart';

import '../theme/app_motion.dart';
import '../theme/app_theme.dart';

/// Logo de Inmobi dibujado en código (sin imagen): el techo de dos rojos, la
/// palabra INMOBI y "BIENES RAÍCES". Se puede animar con [progress] (0 → 1):
///   0.00–0.45  el techo se arma (primero el tramo oscuro, luego el claro)
///   0.30–0.80  aparecen las letras de INMOBI, una por una
///   0.60–1.00  "BIENES RAÍCES" se abre desde el centro
class InmobiLogo extends StatelessWidget {
  const InmobiLogo({
    super.key,
    this.progress = 1,
    this.width = 220,
    this.wordColor = Colors.white,
    this.showWordmark = true,
  });

  final double progress;
  final double width;
  final Color wordColor;
  final bool showWordmark;

  static double _phase(double t, double start, double end) =>
      ((t - start) / (end - start)).clamp(0.0, 1.0);

  @override
  Widget build(BuildContext context) {
    final roofT = _phase(progress, 0, 0.45);
    final wordT = _phase(progress, 0.30, 0.80);
    final subT = _phase(progress, 0.60, 1.0);
    final roofWidth = width * 0.56;

    return SizedBox(
      width: width,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // El techo va corrido a la derecha, como en el logo.
          Padding(
            padding: EdgeInsets.only(left: width * 0.10),
            child: InmobiRoof(width: roofWidth, progress: roofT),
          ),
          if (showWordmark) ...[
            SizedBox(height: width * 0.07),
            // Con letra grande del teléfono o pantallas angostas, se achica
            // en vez de salirse.
            FittedBox(
              fit: BoxFit.scaleDown,
              child: _Wordmark(
                progress: wordT,
                fontSize: width * 0.19,
                color: wordColor,
              ),
            ),
            SizedBox(height: width * 0.035),
            Opacity(
              opacity: Curves.easeOut.transform(subT),
              // Nunca más ancho que el logo: se achica antes que cortarse.
              child: FittedBox(
                fit: BoxFit.scaleDown,
                child: Text(
                  'BIENES RAÍCES',
                  maxLines: 1,
                  softWrap: false,
                  style: TextStyle(
                    fontFamily: AppType.family,
                    fontSize: width * 0.066,
                    fontWeight: FontWeight.w600,
                    color: AppColors.accent,
                    // Se abre desde el centro al aparecer.
                    letterSpacing:
                        width *
                        (0.008 + 0.014 * Curves.easeOutCubic.transform(subT)),
                  ),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _Wordmark extends StatelessWidget {
  const _Wordmark({
    required this.progress,
    required this.fontSize,
    required this.color,
  });

  final double progress;
  final double fontSize;
  final Color color;

  @override
  Widget build(BuildContext context) {
    const letters = 'INMOBI';
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        for (var i = 0; i < letters.length; i++)
          Builder(
            builder: (context) {
              // Cada letra empieza un poco después de la anterior.
              final start = i / (letters.length + 2);
              final t = InmobiLogo._phase(
                progress,
                start,
                start + 3 / (letters.length + 2),
              );
              final eased = Curves.easeOutCubic.transform(t);
              return Opacity(
                opacity: eased,
                child: Transform.translate(
                  offset: Offset(0, (1 - eased) * fontSize * 0.45),
                  child: Padding(
                    padding: EdgeInsets.symmetric(horizontal: fontSize * 0.07),
                    child: Text(
                      letters[i],
                      style: TextStyle(
                        fontFamily: AppType.family,
                        fontSize: fontSize,
                        fontWeight: FontWeight.w400,
                        height: 1,
                        color: color,
                      ),
                    ),
                  ),
                ),
              );
            },
          ),
      ],
    );
  }
}

/// El techo del logo. [progress] arma primero el tramo rojo oscuro (de
/// izquierda a la punta) y después el tramo rojo claro, que crece desde la
/// punta con un pequeño rebote.
class InmobiRoof extends StatelessWidget {
  const InmobiRoof({super.key, this.width = 120, this.progress = 1});

  final double width;
  final double progress;

  // Proporción del dibujo del logo (ancho / alto del techo).
  static const aspect = 255 / 116;

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      size: Size(width, width / aspect),
      painter: _RoofPainter(progress),
    );
  }
}

class _RoofPainter extends CustomPainter {
  _RoofPainter(this.t);

  final double t;

  // Puntos tomados del logo, normalizados al recuadro del techo.
  static const _a = Offset(0, 1); // extremo izquierdo
  static const _b = Offset(0.537, 0); // punta
  static const _c = Offset(0.694, 0.33); // donde el tramo oscuro toca al claro
  static const _d = Offset(1, 0); // esquina superior derecha
  static const _e = Offset(1, 0.98); // base de la "chimenea"

  @override
  void paint(Canvas canvas, Size size) {
    Offset p(Offset o) => Offset(o.dx * size.width, o.dy * size.height);
    final darkT = Curves.easeOutCubic.transform((t / 0.55).clamp(0.0, 1.0));
    final brightRaw = ((t - 0.35) / 0.65).clamp(0.0, 1.0);
    // Rebote suave al terminar de crecer el tramo claro.
    final brightT = brightRaw == 0
        ? 0.0
        : Curves.easeOutBack.transform(brightRaw);

    if (darkT > 0) {
      final a = p(_a);
      final path = Path()
        ..moveTo(a.dx, a.dy)
        ..lineTo(
          Offset.lerp(a, p(_b), darkT)!.dx,
          Offset.lerp(a, p(_b), darkT)!.dy,
        )
        ..lineTo(
          Offset.lerp(a, p(_c), darkT)!.dx,
          Offset.lerp(a, p(_c), darkT)!.dy,
        )
        ..close();
      canvas.drawPath(path, Paint()..color = AppColors.accentDark);
    }

    if (brightT > 0) {
      final b = p(_b);
      Offset grow(Offset o) => b + (p(o) - b) * brightT;
      final d = grow(_d);
      final e = grow(_e);
      final path = Path()
        ..moveTo(b.dx, b.dy)
        ..lineTo(d.dx, d.dy)
        ..lineTo(e.dx, e.dy)
        ..close();
      canvas.drawPath(path, Paint()..color = AppColors.accent);
    }
  }

  @override
  bool shouldRepaint(_RoofPainter old) => old.t != t;
}

/// Fondo de la marca: azul marino con la diagonal más oscura arriba a la
/// derecha, igual que el logo. [reveal] (0 → 1) hace entrar la diagonal.
class InmobiDiagonalBackground extends StatelessWidget {
  const InmobiDiagonalBackground({
    super.key,
    this.reveal = 1,
    this.child,
    this.borderRadius,
  });

  final double reveal;
  final Widget? child;
  final BorderRadius? borderRadius;

  @override
  Widget build(BuildContext context) {
    final content = CustomPaint(
      painter: _DiagonalPainter(reveal),
      child: child,
    );
    if (borderRadius == null) return content;
    return ClipRRect(borderRadius: borderRadius!, child: content);
  }
}

class _DiagonalPainter extends CustomPainter {
  _DiagonalPainter(this.reveal);

  final double reveal;

  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawRect(Offset.zero & size, Paint()..color = AppColors.navy);
    if (reveal <= 0) return;
    final t = Curves.easeOutCubic.transform(reveal.clamp(0.0, 1.0));
    // La diagonal baja desde arriba (a la mitad) hasta el borde derecho.
    final start = Offset(size.width * 0.52, 0);
    final end = Offset(size.width, size.height * 0.74);
    final path = Path()
      ..moveTo(start.dx + (size.width - start.dx) * (1 - t), 0)
      ..lineTo(size.width, 0)
      ..lineTo(size.width, end.dy * t)
      ..close();
    canvas.drawPath(path, Paint()..color = AppColors.navyDeep);
  }

  @override
  bool shouldRepaint(_DiagonalPainter old) => old.reveal != reveal;
}

/// Reproduce la animación del logo una vez (o la muestra quieta si el
/// teléfono pide menos movimiento). [onFinished] avisa al terminar.
class AnimatedInmobiLogo extends StatefulWidget {
  const AnimatedInmobiLogo({
    super.key,
    this.width = 220,
    this.wordColor = Colors.white,
    this.duration = const Duration(milliseconds: 1500),
    this.delay = Duration.zero,
    this.onFinished,
    this.showWordmark = true,
  });

  final double width;
  final Color wordColor;
  final Duration duration;
  final Duration delay;
  final VoidCallback? onFinished;
  final bool showWordmark;

  @override
  State<AnimatedInmobiLogo> createState() => _AnimatedInmobiLogoState();
}

class _AnimatedInmobiLogoState extends State<AnimatedInmobiLogo>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: widget.duration,
  );
  bool _started = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_started) return;
    _started = true;
    if (AppMotion.reduced(context)) {
      _c.value = 1;
      WidgetsBinding.instance.addPostFrameCallback(
        (_) => widget.onFinished?.call(),
      );
      return;
    }
    Future.delayed(widget.delay, () {
      if (!mounted) return;
      _c.forward().whenComplete(() {
        if (mounted) widget.onFinished?.call();
      });
    });
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _c,
      builder: (context, _) => InmobiLogo(
        progress: _c.value,
        width: widget.width,
        wordColor: widget.wordColor,
        showWordmark: widget.showWordmark,
      ),
    );
  }
}
