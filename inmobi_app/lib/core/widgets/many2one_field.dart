import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../api/odoo_client.dart';
import '../theme/app_theme.dart';
import '../../features/contacts/contact_form_screen.dart';
import 'odoo_image.dart';

class Many2oneValue {
  final int id;
  final String name;
  final String? subtitle;
  final String? model;

  const Many2oneValue(
    this.id,
    this.name, {
    this.subtitle,
    this.model,
  });
}

/// Campo tipo "relación" (property_id, partner_id, stage_id, etc.)
/// — al tocarlo abre un buscador enriquecido con imágenes y detalles,
/// permitiendo reconocer visualmente propiedades, clientes y registros.
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
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colors = AppColors.of(context);

    // Vista previa enriquecida para Propiedades seleccionadas
    if (value != null && model == 'estate.property') {
      return Container(
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF1E1A3E) : Colors.white,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: isDark ? const Color(0xFF28235D) : const Color(0xFFD4D4E8),
            width: 1.2,
          ),
          boxShadow: softShadow(opacity: isDark ? 0.2 : 0.04, isDark: isDark),
        ),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: BorderRadius.circular(14),
            onTap: () => _pick(context),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              child: Row(
                children: [
                  ClipRRect(
                    borderRadius: BorderRadius.circular(10),
                    child: SizedBox(
                      width: 46,
                      height: 46,
                      child: OdooImage(
                        odoo: odoo,
                        model: 'estate.property',
                        id: value!.id,
                        field: 'image_main',
                        width: 120,
                        height: 120,
                        errorBuilder: (_) => Container(
                          color: colors.navy.withValues(alpha: 0.08),
                          child: Icon(
                            Icons.home_work_outlined,
                            size: 22,
                            color: colors.navy,
                          ),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          required ? '$label *' : label,
                          style: const TextStyle(
                            fontSize: 10.5,
                            fontWeight: FontWeight.w600,
                            color: Color(0xFFD81F26),
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          value!.name,
                          style: const TextStyle(
                            fontSize: 13.5,
                            fontWeight: FontWeight.w700,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        if (value!.subtitle != null && value!.subtitle!.isNotEmpty)
                          Text(
                            value!.subtitle!,
                            style: TextStyle(
                              fontSize: 11,
                              color: colors.muted,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close_rounded, size: 18),
                    tooltip: 'Quitar selección',
                    onPressed: () => onChanged(null),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    }

    // Vista previa enriquecida para Contactos seleccionados
    if (value != null && model == 'res.partner') {
      return Container(
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF1E1A3E) : Colors.white,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: isDark ? const Color(0xFF28235D) : const Color(0xFFD4D4E8),
            width: 1.2,
          ),
          boxShadow: softShadow(opacity: isDark ? 0.2 : 0.04, isDark: isDark),
        ),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: BorderRadius.circular(14),
            onTap: () => _pick(context),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 20,
                    backgroundColor: const Color(0xFF28235D).withValues(alpha: 0.1),
                    child: Text(
                      value!.name.isNotEmpty ? value!.name[0].toUpperCase() : '?',
                      style: const TextStyle(
                        color: Color(0xFF28235D),
                        fontWeight: FontWeight.w800,
                        fontSize: 14,
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          required ? '$label *' : label,
                          style: const TextStyle(
                            fontSize: 10.5,
                            fontWeight: FontWeight.w600,
                            color: Color(0xFF28235D),
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          value!.name,
                          style: const TextStyle(
                            fontSize: 13.5,
                            fontWeight: FontWeight.w700,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        if (value!.subtitle != null && value!.subtitle!.isNotEmpty)
                          Text(
                            value!.subtitle!,
                            style: TextStyle(
                              fontSize: 11,
                              color: colors.muted,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close_rounded, size: 18),
                    tooltip: 'Quitar selección',
                    onPressed: () => onChanged(null),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    }

    // InputDecorator estándar cuando no hay selección o es otro modelo
    return InkWell(
      borderRadius: BorderRadius.circular(14),
      onTap: () => _pick(context),
      child: InputDecorator(
        decoration: InputDecoration(
          labelText: required ? '$label *' : label,
          suffixIcon: value != null
              ? IconButton(
                  icon: const Icon(Icons.close_rounded, size: 18),
                  onPressed: () => onChanged(null),
                )
              : const Icon(Icons.search_rounded),
        ),
        child: Text(
          value?.name ?? 'Toca para elegir…',
          style: TextStyle(
            color: value != null ? (isDark ? Colors.white : colors.ink) : colors.mutedLight,
            fontWeight: value != null ? FontWeight.w600 : FontWeight.normal,
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
  List<_SearchResultItem> _results = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _search('');
  }

  Future<void> _search(String text) async {
    setState(() => _loading = true);
    try {
      final isProperty = widget.model == 'estate.property';
      final isPartner = widget.model == 'res.partner';

      final List<dynamic> domain = [...widget.domain];
      final query = text.trim();

      if (query.isNotEmpty) {
        if (isProperty) {
          domain.addAll([
            '|',
            '|',
            ['name', 'ilike', query],
            ['title', 'ilike', query],
            ['city', 'ilike', query],
          ]);
        } else if (isPartner) {
          domain.addAll([
            '|',
            '|',
            ['name', 'ilike', query],
            ['phone', 'ilike', query],
            ['email', 'ilike', query],
          ]);
        } else {
          domain.add([widget.searchField, 'ilike', query]);
        }
      }

      final fields = <String>[
        widget.searchField,
        if (isProperty) ...['title', 'price', 'city', 'sector', 'state', 'property_type_id'],
        if (isPartner) ...['phone', 'mobile', 'email', 'city'],
      ];

      final rows = await widget.odoo.searchRead(
        model: widget.model,
        domain: domain,
        fields: fields,
        limit: 40,
        order: isProperty ? 'write_date desc' : '${widget.searchField} asc',
      );

      final currency = NumberFormat.currency(
        symbol: r'$',
        decimalDigits: 0,
        locale: 'es_EC',
      );

      setState(() {
        _results = rows.map((r) {
          final id = r['id'] as int;
          String name = (r[widget.searchField] ?? '').toString();
          String? subtitle;

          if (isProperty) {
            final title = (r['title'] ?? '').toString();
            if (title.isNotEmpty) name = title;
            final price = r['price'] is num ? (r['price'] as num).toDouble() : 0.0;
            final city = (r['city'] ?? '').toString();
            final sector = (r['sector'] ?? '').toString();
            final location = [city, sector].where((s) => s.isNotEmpty).join(', ');

            subtitle = [
              if (location.isNotEmpty) '📍 $location',
              if (price > 0) currency.format(price),
            ].join(' · ');
          } else if (isPartner) {
            final rawPhone = r['phone'];
            final rawMobile = r['mobile'];
            final rawEmail = r['email'];
            final phone = (rawPhone != null && rawPhone != false && rawPhone.toString() != 'false')
                ? rawPhone.toString()
                : ((rawMobile != null && rawMobile != false && rawMobile.toString() != 'false')
                    ? rawMobile.toString()
                    : '');
            final email = (rawEmail != null && rawEmail != false && rawEmail.toString() != 'false')
                ? rawEmail.toString()
                : '';
            subtitle = [
              if (phone.isNotEmpty) '📞 $phone',
              if (email.isNotEmpty) email,
            ].join(' · ');
          }

          return _SearchResultItem(
            id: id,
            name: name,
            subtitle: subtitle,
            model: widget.model,
            rawData: r,
          );
        }).toList();
      });
    } catch (_) {
      setState(() => _results = []);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _createNewContact() async {
    final result = await Navigator.of(context).push<dynamic>(
      MaterialPageRoute(builder: (_) => const ContactFormScreen()),
    );
    if (result != null && result is int) {
      try {
        final rows = await widget.odoo.searchRead(
          model: 'res.partner',
          domain: [
            ['id', '=', result],
          ],
          fields: ['name', 'phone', 'mobile', 'email'],
          limit: 1,
        );
        if (rows.isNotEmpty && mounted) {
          final row = rows.first;
          final name = (row['name'] ?? 'Nuevo Contacto').toString();
          final rawPhone = row['phone'];
          final rawMobile = row['mobile'];
          final phone = (rawPhone != null && rawPhone != false && rawPhone.toString() != 'false')
              ? rawPhone.toString()
              : ((rawMobile != null && rawMobile != false && rawMobile.toString() != 'false')
                  ? rawMobile.toString()
                  : '');
          Navigator.of(context).pop(
            Many2oneValue(
              result,
              name,
              subtitle: phone.isNotEmpty ? '📞 $phone' : null,
              model: 'res.partner',
            ),
          );
          return;
        }
      } catch (_) {}
    }
    _search(_searchCtrl.text);
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colors = AppColors.of(context);
    final isProperty = widget.model == 'estate.property';
    final isPartner = widget.model == 'res.partner';

    return Scaffold(
      appBar: AppBar(
        title: Text('Seleccionar ${widget.title}'),
        actions: [
          if (isPartner)
            TextButton.icon(
              onPressed: _createNewContact,
              icon: const Icon(Icons.person_add_alt_1_rounded, size: 18, color: Color(0xFFD81F26)),
              label: const Text(
                'Nuevo',
                style: TextStyle(
                  color: Color(0xFFD81F26),
                  fontWeight: FontWeight.w800,
                  fontSize: 13,
                ),
              ),
            ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
            child: TextField(
              controller: _searchCtrl,
              autofocus: true,
              decoration: InputDecoration(
                hintText: isProperty
                    ? 'Buscar propiedad por título, sector, ciudad...'
                    : isPartner
                        ? 'Buscar contacto por nombre, teléfono, email...'
                        : 'Buscar ${widget.title.toLowerCase()}...',
                prefixIcon: const Icon(Icons.search_rounded),
                suffixIcon: _searchCtrl.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.close_rounded, size: 20),
                        onPressed: () {
                          _searchCtrl.clear();
                          _search('');
                        },
                      )
                    : null,
              ),
              onChanged: _search,
            ),
          ),
          if (_loading) const LinearProgressIndicator(minHeight: 2),
          Expanded(
            child: _results.isEmpty && !_loading
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            isProperty
                                ? Icons.home_work_outlined
                                : isPartner
                                    ? Icons.person_search_outlined
                                    : Icons.search_off_rounded,
                            size: 48,
                            color: colors.mutedLight,
                          ),
                          const SizedBox(height: 10),
                          Text(
                            'No se encontraron resultados.',
                            style: TextStyle(
                              color: colors.muted,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          if (isPartner) ...[
                            const SizedBox(height: 14),
                            ElevatedButton.icon(
                              style: ElevatedButton.styleFrom(
                                backgroundColor: const Color(0xFF28235D),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(12),
                                ),
                              ),
                              onPressed: _createNewContact,
                              icon: const Icon(Icons.person_add_alt_1_rounded, size: 18, color: Colors.white),
                              label: const Text(
                                'Crear contacto rápido',
                                style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  )
                : ListView.separated(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
                    itemCount: _results.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 8),
                    itemBuilder: (context, i) {
                      final item = _results[i];
                      return Container(
                        decoration: BoxDecoration(
                          color: isDark ? const Color(0xFF1E1A3E) : Colors.white,
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(
                            color: isDark ? Colors.white12 : const Color(0xFFE2E8F0),
                          ),
                        ),
                        child: Material(
                          color: Colors.transparent,
                          child: InkWell(
                            borderRadius: BorderRadius.circular(14),
                            onTap: () => Navigator.of(context).pop(
                              Many2oneValue(
                                item.id,
                                item.name,
                                subtitle: item.subtitle,
                                model: item.model,
                              ),
                            ),
                            child: Padding(
                              padding: const EdgeInsets.all(10),
                              child: Row(
                                children: [
                                  // Imagen miniatura para propiedades
                                  if (isProperty)
                                    ClipRRect(
                                      borderRadius: BorderRadius.circular(10),
                                      child: SizedBox(
                                        width: 52,
                                        height: 52,
                                        child: OdooImage(
                                          odoo: widget.odoo,
                                          model: 'estate.property',
                                          id: item.id,
                                          field: 'image_main',
                                          width: 140,
                                          height: 140,
                                          errorBuilder: (_) => Container(
                                            color: const Color(0xFF28235D).withValues(alpha: 0.08),
                                            child: const Icon(
                                              Icons.home_work_outlined,
                                              size: 24,
                                              color: Color(0xFF28235D),
                                            ),
                                          ),
                                        ),
                                      ),
                                    )
                                  else if (isPartner)
                                    CircleAvatar(
                                      radius: 22,
                                      backgroundColor: const Color(0xFF28235D).withValues(alpha: 0.1),
                                      child: Text(
                                        item.name.isNotEmpty ? item.name[0].toUpperCase() : '?',
                                        style: const TextStyle(
                                          color: Color(0xFF28235D),
                                          fontWeight: FontWeight.w800,
                                          fontSize: 15,
                                        ),
                                      ),
                                    )
                                  else
                                    Container(
                                      width: 44,
                                      height: 44,
                                      decoration: BoxDecoration(
                                        color: const Color(0xFF28235D).withValues(alpha: 0.08),
                                        borderRadius: BorderRadius.circular(10),
                                      ),
                                      child: const Icon(
                                        Icons.check_circle_outline_rounded,
                                        color: Color(0xFF28235D),
                                        size: 20,
                                      ),
                                    ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          item.name,
                                          style: const TextStyle(
                                            fontSize: 14,
                                            fontWeight: FontWeight.w700,
                                          ),
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                        if (item.subtitle != null && item.subtitle!.isNotEmpty) ...[
                                          const SizedBox(height: 3),
                                          Text(
                                            item.subtitle!,
                                            style: TextStyle(
                                              fontSize: 12,
                                              color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                                              fontWeight: FontWeight.w500,
                                            ),
                                            maxLines: 1,
                                            overflow: TextOverflow.ellipsis,
                                          ),
                                        ],
                                      ],
                                    ),
                                  ),
                                  Icon(
                                    Icons.chevron_right_rounded,
                                    color: colors.mutedLight,
                                    size: 20,
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}

class _SearchResultItem {
  final int id;
  final String name;
  final String? subtitle;
  final String model;
  final Map<String, dynamic> rawData;

  const _SearchResultItem({
    required this.id,
    required this.name,
    this.subtitle,
    required this.model,
    required this.rawData,
  });
}
