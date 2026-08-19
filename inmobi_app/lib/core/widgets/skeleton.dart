import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// Bloque con un brillo animado que recorre de lado a lado — el placeholder
/// "esqueleto" que se ve mientras carga una lista, en vez de un spinner
/// suelto en medio de la pantalla. Sensación mucho más pulida en apps reales.
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
  late final AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1300),
    )..repeat();
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _ctrl,
      builder: (context, _) {
        return Container(
          width: widget.width,
          height: widget.height,
          decoration: BoxDecoration(
            borderRadius: widget.borderRadius,
            gradient: LinearGradient(
              begin: Alignment(-1 + _ctrl.value * 3, 0),
              end: Alignment(0 + _ctrl.value * 3, 0),
              colors: const [
                AppColors.neutralBg,
                Color(0xFFE4E6EC),
                AppColors.neutralBg,
              ],
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
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            Skeleton(
              width: 64,
              height: 64,
              borderRadius: BorderRadius.circular(10),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Skeleton(
                    width: MediaQuery.of(context).size.width * 0.5,
                    height: 15,
                  ),
                  const SizedBox(height: 8),
                  Skeleton(
                    width: MediaQuery.of(context).size.width * 0.3,
                    height: 12,
                  ),
                  const SizedBox(height: 10),
                  Skeleton(width: 90, height: 12),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Lista completa de esqueletos, para reemplazar el spinner de carga en las
/// pantallas de listado.
class SkeletonList extends StatelessWidget {
  final int count;
  const SkeletonList({super.key, this.count = 6});

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
      itemCount: count,
      separatorBuilder: (_, _) => const SizedBox(height: 10),
      itemBuilder: (_, _) => const SkeletonListCard(),
    );
  }
}
