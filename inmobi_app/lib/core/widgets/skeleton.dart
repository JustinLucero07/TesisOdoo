import 'package:flutter/material.dart';

import '../theme/app_motion.dart';
import '../theme/app_theme.dart';

/// Bloque con un brillo que recorre de lado a lado — el placeholder que se ve
/// mientras carga una lista, en vez de un spinner suelto en medio de la
/// pantalla. El esqueleto ya tiene la forma del contenido que viene, así que
/// la pantalla no salta cuando los datos llegan.
class Skeleton extends StatefulWidget {
  final double? width;
  final double height;
  final BorderRadius borderRadius;

  const Skeleton({
    super.key,
    this.width,
    this.height = 14,
    this.borderRadius = const BorderRadius.all(Radius.circular(6)),
  });

  @override
  State<Skeleton> createState() => _SkeletonState();
}

class _SkeletonState extends State<Skeleton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1400),
  )..repeat();

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.of(context);
    final base = colors.isDark ? colors.surfaceAlt : colors.neutralBg;
    // El brillo se mantiene sutil a propósito: un destello fuerte repitiéndose
    // cada segundo cansa la vista mientras se espera.
    final shine = colors.isDark
        ? Color.lerp(base, Colors.white, 0.07)!
        : Color.lerp(base, Colors.white, 0.75)!;

    // Con movimiento reducido el bloque se queda quieto: sigue comunicando
    // "esto está cargando" por la forma, sin nada oscilando en pantalla.
    if (AppMotion.reduced(context)) {
      return Container(
        width: widget.width,
        height: widget.height,
        decoration: BoxDecoration(color: base, borderRadius: widget.borderRadius),
      );
    }

    return AnimatedBuilder(
      animation: _ctrl,
      builder: (context, _) {
        final t = Curves.easeInOut.transform(_ctrl.value);
        return Container(
          width: widget.width,
          height: widget.height,
          decoration: BoxDecoration(
            borderRadius: widget.borderRadius,
            gradient: LinearGradient(
              begin: Alignment(-1.6 + t * 3.2, -0.3),
              end: Alignment(-0.6 + t * 3.2, 0.3),
              colors: [base, shine, base],
              stops: const [0.0, 0.5, 1.0],
            ),
          ),
        );
      },
    );
  }
}

/// Fila de esqueleto que imita una tarjeta de lista (foto + 3 líneas de
/// texto) — usado mientras cargan Propiedades, Leads, Visitas y Contratos.
class SkeletonListCard extends StatelessWidget {
  const SkeletonListCard({super.key});

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            Skeleton(
              width: 64,
              height: 64,
              borderRadius: BorderRadius.circular(12),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Skeleton(width: width * 0.5, height: 15),
                  const SizedBox(height: 8),
                  Skeleton(width: width * 0.3, height: 12),
                  const SizedBox(height: 10),
                  const Skeleton(width: 90, height: 12),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Lista completa de esqueletos. Cada tarjeta entra un instante después de la
/// anterior, así la espera se siente como algo que se está armando y no como
/// una pantalla congelada.
class SkeletonList extends StatelessWidget {
  final int count;
  final EdgeInsetsGeometry padding;

  const SkeletonList({
    super.key,
    this.count = 6,
    this.padding = const EdgeInsets.fromLTRB(16, 4, 16, 16),
  });

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      padding: padding,
      itemCount: count,
      physics: const NeverScrollableScrollPhysics(),
      separatorBuilder: (_, _) => const SizedBox(height: 10),
      itemBuilder: (_, i) => _StaggeredFade(
        index: i,
        child: const SkeletonListCard(),
      ),
    );
  }
}

/// Desvanecido escalonado propio del esqueleto — no reutiliza `FadeSlideIn`
/// porque aquí no debe desplazarse nada: el bloque ya está en su sitio, solo
/// aparece.
class _StaggeredFade extends StatefulWidget {
  final Widget child;
  final int index;

  const _StaggeredFade({required this.child, required this.index});

  @override
  State<_StaggeredFade> createState() => _StaggeredFadeState();
}

class _StaggeredFadeState extends State<_StaggeredFade>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl = AnimationController(
    vsync: this,
    duration: AppMotion.normal,
  );

  @override
  void initState() {
    super.initState();
    Future<void>.delayed(
      Duration(milliseconds: 50 * widget.index.clamp(0, 6)),
      () {
        if (mounted) _ctrl.forward();
      },
    );
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (AppMotion.reduced(context)) return widget.child;
    return FadeTransition(
      opacity: CurvedAnimation(parent: _ctrl, curve: AppMotion.curve),
      child: widget.child,
    );
  }
}
