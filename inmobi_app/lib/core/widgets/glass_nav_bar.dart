import 'package:flutter/material.dart';
import 'package:flutter/physics.dart';
import 'package:flutter/services.dart';

import '../theme/app_motion.dart';
import '../theme/app_theme.dart';
import 'glass.dart';

class GlassNavItem {
  final IconData icon;
  final IconData activeIcon;
  final String label;

  const GlassNavItem({
    required this.icon,
    required this.activeIcon,
    required this.label,
  });
}

/// Barra de navegación flotante de vidrio: no ocupa una franja fija del
/// fondo, flota sobre el contenido y deja que este se vea desenfocado por
/// debajo.
///
/// El indicador de la sección activa no salta: se desliza con un resorte que
/// arrastra la velocidad que traía. Si tocas otra pestaña mientras todavía se
/// está moviendo, cambia de rumbo desde donde va, sin frenar en seco.
class GlassNavBar extends StatefulWidget {
  final int currentIndex;
  final ValueChanged<int> onTap;
  final List<GlassNavItem> items;

  const GlassNavBar({
    super.key,
    required this.currentIndex,
    required this.onTap,
    required this.items,
  });

  /// Alto que ocupa la barra + su margen, para que el contenido de las
  /// pantallas reserve ese espacio al final y nada quede tapado.
  static const double reservedHeight = 96;

  @override
  State<GlassNavBar> createState() => _GlassNavBarState();
}

class _GlassNavBarState extends State<GlassNavBar>
    with SingleTickerProviderStateMixin {
  /// Posición del indicador medida en "índices" (2.4 = entre la 2 y la 3).
  /// Va sin límites porque el resorte puede pasarse un poco del destino.
  late final AnimationController _indicator = AnimationController.unbounded(
    vsync: this,
    value: widget.currentIndex.toDouble(),
  );

  @override
  void didUpdateWidget(covariant GlassNavBar old) {
    super.didUpdateWidget(old);
    if (widget.currentIndex != old.currentIndex) _moveIndicator();
  }

  void _moveIndicator() {
    final target = widget.currentIndex.toDouble();
    if (AppMotion.reduced(context)) {
      _indicator.value = target;
      return;
    }
    // Arranca desde donde está *ahora* y con la velocidad que trae: así un
    // cambio a mitad de camino no produce un salto ni un frenazo.
    _indicator.animateWith(
      SpringSimulation(
        AppMotion.spring,
        _indicator.value,
        target,
        _indicator.velocity,
      ),
    );
  }

  @override
  void dispose() {
    _indicator.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.of(context);
    final bottomInset = MediaQuery.viewPaddingOf(context).bottom;

    return Padding(
      padding: EdgeInsets.fromLTRB(14, 0, 14, bottomInset > 0 ? bottomInset : 14),
      child: GlassSurface(
        level: GlassLevel.thick,
        borderRadius: const BorderRadius.all(Radius.circular(30)),
        child: SizedBox(
          height: 62,
          child: LayoutBuilder(
            builder: (context, constraints) {
              final itemWidth = constraints.maxWidth / widget.items.length;

              return Stack(
                children: [
                  // Pastilla sólida detrás de la sección activa. Va sólida a
                  // propósito: el color sobre vidrio se pone en una capa
                  // opaca, nunca en el texto translúcido.
                  AnimatedBuilder(
                    animation: _indicator,
                    builder: (context, _) => Positioned(
                      left: _indicator.value * itemWidth + 8,
                      top: 7,
                      width: itemWidth - 16,
                      height: 48,
                      child: DecoratedBox(
                        decoration: BoxDecoration(
                          color: colors.navy,
                          borderRadius: BorderRadius.circular(22),
                          boxShadow: [
                            BoxShadow(
                              color: colors.navy.withValues(alpha: 0.32),
                              blurRadius: 12,
                              offset: const Offset(0, 4),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  Row(
                    children: List.generate(widget.items.length, (i) {
                      return Expanded(
                        child: _NavButton(
                          item: widget.items[i],
                          selected: i == widget.currentIndex,
                          onTap: () {
                            if (i == widget.currentIndex) return;
                            HapticFeedback.selectionClick();
                            widget.onTap(i);
                          },
                        ),
                      );
                    }),
                  ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}

class _NavButton extends StatelessWidget {
  final GlassNavItem item;
  final bool selected;
  final VoidCallback onTap;

  const _NavButton({
    required this.item,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.of(context);
    // Sobre vidrio el texto no puede ser gris plano: se pierde cuando el
    // fondo cambia al hacer scroll. Va con más peso y más contraste.
    final onPill = colors.isDark ? colors.ink : Colors.white;
    final resting = colors.muted;

    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: AnimatedDefaultTextStyle(
        duration: AppMotion.duration(context, AppMotion.normal),
        curve: AppMotion.curve,
        style: TextStyle(
          fontFamily: AppType.family,
          fontSize: 10.5,
          fontWeight: selected ? FontWeight.w700 : FontWeight.w600,
          letterSpacing: 0.1,
          color: selected ? onPill : resting,
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            TweenAnimationBuilder<double>(
              tween: Tween(end: selected ? 1 : 0),
              duration: AppMotion.duration(context, AppMotion.normal),
              curve: AppMotion.curve,
              builder: (context, t, child) => Transform.scale(
                scale: 1 + 0.08 * t,
                child: Icon(
                  selected ? item.activeIcon : item.icon,
                  size: 21,
                  color: Color.lerp(resting, onPill, t),
                ),
              ),
            ),
            const SizedBox(height: 3),
            Text(item.label, maxLines: 1, overflow: TextOverflow.ellipsis),
          ],
        ),
      ),
    );
  }
}
