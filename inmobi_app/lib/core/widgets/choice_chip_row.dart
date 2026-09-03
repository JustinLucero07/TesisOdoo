import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

class ChoiceChipRow extends StatelessWidget {
  final List<(String?, String)> options;
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
    final colors = AppColors.of(context);
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
            selectedColor: colors.navy,
            backgroundColor: colors.neutralBg,
            labelStyle: TextStyle(
              color: selected ? Colors.white : colors.ink,
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
