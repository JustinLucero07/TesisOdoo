import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../theme/app_theme.dart';

/// Botón rojo de "crear" que va al lado del buscador. Reemplaza al botón
/// flotante, que tapaba tarjetas y botones encima de la barra de navegación.
class AddSquareButton extends StatelessWidget {
  const AddSquareButton({
    super.key,
    required this.onTap,
    required this.tooltip,
    this.icon = Icons.add_rounded,
  });

  final VoidCallback onTap;
  final String tooltip;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: Material(
        color: AppColors.accent,
        borderRadius: BorderRadius.circular(14),
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: () {
            HapticFeedback.lightImpact();
            onTap();
          },
          child: SizedBox(
            width: 44,
            height: 44,
            child: Icon(icon, color: Colors.white, size: 22),
          ),
        ),
      ),
    );
  }
}
