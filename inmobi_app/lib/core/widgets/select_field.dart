import 'package:flutter/material.dart';

/// Campo para un `fields.Selection` de Odoo (offer_type, appointment_type,
/// visit_state, etc.) — lista fija de opciones, sin necesidad de consultar
/// al backend.
class SelectField extends StatelessWidget {
  final String label;
  final String? value;
  final List<(String, String)> options; // (valor_odoo, etiqueta_visible)
  final ValueChanged<String?> onChanged;

  const SelectField({
    super.key,
    required this.label,
    required this.value,
    required this.options,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return DropdownButtonFormField<String>(
      initialValue: value,
      decoration: InputDecoration(labelText: label),
      items: options
          .map(
            (o) => DropdownMenuItem(
              value: o.$1,
              child: Text(o.$2, overflow: TextOverflow.ellipsis),
            ),
          )
          .toList(),
      onChanged: onChanged,
    );
  }
}
