import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// Fila horizontal de chips de selección única — usada como filtro rápido
/// bajo el buscador en las listas (Propiedades, CRM, Contratos, Agenda).
/// `null` representa "Todos".
class ChoiceChipRow extends StatelessWidget {
  final List<(String?, String)> options; // (valor_odoo o null, etiqueta)
  final String? value;
  final ValueChanged<String?> onChanged;

  const ChoiceChipRow({
    super.key,
    required this.options,
    required this.value,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 36,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16),
        itemCount: options.length,
        separatorBuilder: (_, _) => const SizedBox(width: 8),
        itemBuilder: (context, i) {
          final (optValue, label) = options[i];
          final selected = optValue == value;
          return ChoiceChip(
            label: Text(label),
            selected: selected,
            onSelected: (_) => onChanged(optValue),
            selectedColor: AppColors.navy,
            backgroundColor: AppColors.neutralBg,
            labelStyle: TextStyle(
              color: selected ? Colors.white : AppColors.ink,
              fontWeight: FontWeight.w600,
              fontSize: 12.5,
            ),
            side: BorderSide.none,
            showCheckmark: false,
          );
        },
      ),
    );
  }
}
