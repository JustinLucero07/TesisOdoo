import 'package:flutter/material.dart';

import '../api/odoo_client.dart';
import '../theme/app_theme.dart';

class Many2oneValue {
  final int id;
  final String name;
  const Many2oneValue(this.id, this.name);
}

/// Campo tipo "relación" (property_id, stage_id, target_property_id, etc.)
/// — al tocarlo abre un buscador de pantalla completa contra el modelo de
/// Odoo indicado (mismo `search_read` que usa el resto de la app) y permite
/// elegir un registro. No hace falta traer la lista completa de antemano:
/// busca mientras el usuario escribe, igual que el selector del ERP.
class Many2oneField extends StatelessWidget {
  final String label;
  final OdooClient odoo;
  final String model;
  final String searchField;
  final Many2oneValue? value;
  final ValueChanged<Many2oneValue?> onChanged;
  final bool required;
  final List<dynamic> domain;

  const Many2oneField({
    super.key,
    required this.label,
    required this.odoo,
    required this.model,
    required this.onChanged,
    this.searchField = 'name',
    this.value,
    this.required = false,
    this.domain = const [],
  });

  Future<void> _pick(BuildContext context) async {
    final result = await Navigator.of(context).push<Many2oneValue>(
      MaterialPageRoute(
        builder: (_) => _Many2oneSearchScreen(
          title: label,
          odoo: odoo,
          model: model,
          searchField: searchField,
          domain: domain,
        ),
      ),
    );
    if (result != null) onChanged(result);
  }

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: () => _pick(context),
      child: InputDecorator(
        decoration: InputDecoration(
          labelText: required ? '$label *' : label,
          suffixIcon: value != null
              ? IconButton(
                  icon: const Icon(Icons.close, size: 18),
                  onPressed: () => onChanged(null),
                )
              : const Icon(Icons.search),
        ),
        child: Text(
          value?.name ?? 'Toca para elegir…',
          style: TextStyle(
            color: value != null ? AppColors.ink : AppColors.mutedLight,
          ),
          overflow: TextOverflow.ellipsis,
        ),
      ),
    );
  }
}

class _Many2oneSearchScreen extends StatefulWidget {
  final String title;
  final OdooClient odoo;
  final String model;
  final String searchField;
  final List<dynamic> domain;

  const _Many2oneSearchScreen({
    required this.title,
    required this.odoo,
    required this.model,
    required this.searchField,
    required this.domain,
  });

  @override
  State<_Many2oneSearchScreen> createState() => _Many2oneSearchScreenState();
}

class _Many2oneSearchScreenState extends State<_Many2oneSearchScreen> {
  final _searchCtrl = TextEditingController();
  List<Many2oneValue> _results = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _search('');
  }

  Future<void> _search(String text) async {
    setState(() => _loading = true);
    try {
      final domain = [
        ...widget.domain,
        if (text.trim().isNotEmpty) [widget.searchField, 'ilike', text.trim()],
      ];
      final rows = await widget.odoo.searchRead(
        model: widget.model,
        domain: domain,
        fields: [widget.searchField],
        limit: 30,
        order: '${widget.searchField} asc',
      );
      setState(() {
        _results = rows
            .map(
              (r) => Many2oneValue(
                r['id'] as int,
                (r[widget.searchField] ?? '').toString(),
              ),
            )
            .toList();
      });
    } catch (_) {
      setState(() => _results = []);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.title)),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: TextField(
              controller: _searchCtrl,
              autofocus: true,
              decoration: const InputDecoration(
                hintText: 'Buscar...',
                prefixIcon: Icon(Icons.search),
              ),
              onChanged: _search,
            ),
          ),
          if (_loading) const LinearProgressIndicator(),
          Expanded(
            child: _results.isEmpty && !_loading
                ? const Center(
                    child: Text(
                      'Sin resultados',
                      style: TextStyle(color: AppColors.muted),
                    ),
                  )
                : ListView.separated(
                    itemCount: _results.length,
                    separatorBuilder: (_, _) => const Divider(height: 1),
                    itemBuilder: (context, i) {
                      final item = _results[i];
                      return ListTile(
                        title: Text(item.name),
                        onTap: () => Navigator.of(context).pop(item),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}
