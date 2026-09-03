import 'dart:ui' show lerpDouble;

import 'package:flutter/foundation.dart';
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
/// Dos movimientos, los dos con resorte y los dos interrumpibles:
///
/// * **El indicador** de la sección activa no salta: se desliza arrastrando la
///   velocidad que traía. Si tocas otra pestaña mientras todavía se mueve,
///   cambia de rumbo desde donde va, sin frenar en seco.
/// * **La barra se compacta al bajar** por el contenido: las etiquetas se
///   pliegan y quedan solo los íconos, para devolverle pantalla a lo que
///   estás leyendo. Al subir, vuelve a crecer. Se controla desde afuera con
///   [collapsed] para que la barra no tenga que saber quién hace scroll.
class GlassNavBar extends StatefulWidget {
  final int currentIndex;
  final ValueChanged<int> onTap;
  final List<GlassNavItem> items;

  /// Señal externa de "compáctate". Va como `ValueListenable` y no como un
  /// simple `bool` para que quien hace scroll no tenga que reconstruir toda
  /// la pantalla en cada cambio de dirección: solo se repinta esta barra.
  final ValueListenable<bool>? collapsed;

  const GlassNavBar({
    super.key,
    required this.currentIndex,
    required this.onTap,
    required this.items,
    this.collapsed,
  });

  /// Alto que ocupa la barra + su margen, para que el contenido de las
  /// pantallas reserve ese espacio al final y nada quede tapado. Se mantiene
  /// en el tamaño expandido: si encogiera junto con la barra, el contenido
  /// daría un brinco cada vez que esta se compacta.
  static const double reservedHeight = 96;

  static const double _expandedHeight = 62;
  static const double _collapsedHeight = 50;

  @override
  State<GlassNavBar> createState() => _GlassNavBarState();
}

class _GlassNavBarState extends State<GlassNavBar>
    with TickerProviderStateMixin {
  /// Posición del indicador medida en "índices" (2.4 = entre la 2 y la 3).
  /// Va sin límites porque el resorte puede pasarse un poco del destino.
  late final AnimationController _indicator = AnimationController.unbounded(
    vsync: this,
    value: widget.currentIndex.toDouble(),
  );

  /// 0 = barra completa con etiquetas · 1 = compacta, solo íconos.
  late final AnimationController _collapse = AnimationController.unbounded(
    vsync: this,
    value: 0,
  );

  @override
  void initState() {
    super.initState();
    widget.collapsed?.addListener(_onCollapsedChanged);
  }

  @override
  void didUpdateWidget(covariant GlassNavBar old) {
    super.didUpdateWidget(old);
    if (widget.currentIndex != old.currentIndex) _moveIndicator();
    if (widget.collapsed != old.collapsed) {
      old.collapsed?.removeListener(_onCollapsedChanged);
      widget.collapsed?.addListener(_onCollapsedChanged);
    }
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

  void _onCollapsedChanged() {
    final target = (widget.collapsed?.value ?? false) ? 1.0 : 0.0;
    if (AppMotion.reduced(context)) {
      _collapse.value = target;
      return;
    }
    // Igual que el indicador: sale desde el valor actual con su velocidad,
    // así un cambio rápido de dirección del scroll no corta el movimiento.
    _collapse.animateWith(
      SpringSimulation(
        AppMotion.spring,
        _collapse.value,
        target,
        _collapse.velocity,
      ),
    );
  }

  @override
  void dispose() {
    widget.collapsed?.removeListener(_onCollapsedChanged);
    _indicator.dispose();
    _collapse.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.of(context);
    final bottomInset = MediaQuery.viewPaddingOf(context).bottom;
    final margin = bottomInset > 0 ? bottomInset : 14.0;

    // El hueco exterior se queda fijo y solo se encoge la pastilla de vidrio
    // por dentro: así el Scaffold no rehace su layout en cada fotograma.
    return SizedBox(
      height: GlassNavBar._expandedHeight + margin,
      child: AnimatedBuilder(
        animation: _collapse,
        builder: (context, _) {
          final t = _collapse.value.clamp(0.0, 1.0);
          final height = lerpDouble(
            GlassNavBar._expandedHeight,
            GlassNavBar._collapsedHeight,
            t,
          )!;

          return Align(
            alignment: Alignment.bottomCenter,
            child: Padding(
              // Al compactarse también se angosta un poco: el gesto completo
              // se lee como "me hago a un lado", no solo "pierdo texto".
              padding: EdgeInsets.fromLTRB(
                lerpDouble(14, 30, t)!,
                0,
                lerpDouble(14, 30, t)!,
                margin,
              ),
              child: GlassSurface(
                level: GlassLevel.thick,
                borderRadius: BorderRadius.circular(height / 2),
                child: SizedBox(
                  height: height,
                  child: LayoutBuilder(
                    builder: (context, constraints) {
                      final itemWidth =
                          constraints.maxWidth / widget.items.length;
                      final pillHeight = height - 14;

                      return Stack(
                        children: [
                          // Pastilla sólida detrás de la sección activa. Va
                          // sólida a propósito: el color sobre vidrio se pone
                          // en una capa opaca, nunca en el texto translúcido.
                          AnimatedBuilder(
                            animation: _indicator,
                            builder: (context, _) => Positioned(
                              left: _indicator.value * itemWidth + 8,
                              top: 7,
                              width: itemWidth - 16,
                              height: pillHeight,
                              child: DecoratedBox(
                                decoration: BoxDecoration(
                                  color: colors.navy,
                                  borderRadius: BorderRadius.circular(
                                    pillHeight / 2,
                                  ),
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
                                  collapse: t,
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
            ),
          );
        },
      ),
    );
  }
}

class _NavButton extends StatelessWidget {
  final GlassNavItem item;
  final bool selected;

  /// 0 = con etiqueta · 1 = solo ícono.
  final double collapse;
  final VoidCallback onTap;

  const _NavButton({
    required this.item,
    required this.selected,
    required this.collapse,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.of(context);
    // Sobre vidrio el texto no puede ser gris plano: se pierde cuando el
    // fondo cambia al hacer scroll. Va con más peso y más contraste.
    final onPill = colors.isDark ? colors.ink : Colors.white;
    final resting = colors.muted;

    // La etiqueta se desvanece antes de que termine de plegarse, para que no
    // se vea texto aplastado a la mitad del movimiento.
    final labelOpacity = (1 - collapse * 1.8).clamp(0.0, 1.0);

    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
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
          // Se pliega hacia arriba: el ícono queda centrado en la barra
          // compacta sin que nada salte de posición.
          ClipRect(
            child: Align(
              alignment: Alignment.topCenter,
              heightFactor: (1 - collapse).clamp(0.0, 1.0),
              child: Opacity(
                opacity: labelOpacity,
                child: Padding(
                  padding: const EdgeInsets.only(top: 3),
                  child: Text(
                    item.label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontFamily: AppType.family,
                      fontSize: 10.5,
                      fontWeight: selected ? FontWeight.w700 : FontWeight.w600,
                      letterSpacing: 0.1,
                      color: selected ? onPill : resting,
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
