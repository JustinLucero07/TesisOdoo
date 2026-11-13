import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// Menú "⋯" de la barra superior con la acción de eliminar. Antes la papelera
/// roja estaba a la vista junto a "Editar" y era fácil tocarla sin querer.
class DeleteMenuButton extends StatelessWidget {
  const DeleteMenuButton({
    super.key,
    required this.onDelete,
    required this.label,
    this.enabled = true,
  });

  final VoidCallback onDelete;
  final String label;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.of(context);
    return PopupMenuButton<String>(
      enabled: enabled,
      tooltip: 'Más opciones',
      icon: const Icon(Icons.more_vert_rounded),
      onSelected: (_) => onDelete(),
      itemBuilder: (_) => [
        PopupMenuItem<String>(
          value: 'delete',
          child: Row(
            children: [
              Icon(
                Icons.delete_outline_rounded,
                size: 20,
                color: colors.danger,
              ),
              const SizedBox(width: 10),
              Text(label, style: TextStyle(color: colors.danger)),
            ],
          ),
        ),
      ],
    );
  }
}
