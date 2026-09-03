import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/app_badge.dart';
import '../../core/widgets/choice_chip_row.dart';
import '../../core/widgets/skeleton.dart';
import '../../core/widgets/states.dart';
import '../auth/auth_service.dart';
import 'contact_detail_screen.dart';
import 'contact_form_screen.dart';
import 'contact_model.dart';
import 'contact_service.dart';

/// Directorio de contactos con secciones por letra e índice A-Z lateral,
/// igual que la agenda del teléfono: con miles de contactos, desplazarse a
/// mano no es viable.
class ContactListScreen extends StatefulWidget {
  const ContactListScreen({super.key});

  @override
  State<ContactListScreen> createState() => _ContactListScreenState();
}

class _ContactListScreenState extends State<ContactListScreen> {
  late final ContactService _service;
  final _searchCtrl = TextEditingController();
  final _scrollController = ScrollController();
  String? _roleFilter;

  List<Contact> _contacts = [];
  bool _loading = true;
  String? _error;

  /// Índices dentro de la lista aplanada donde arranca cada letra, para que
  /// el índice lateral pueda saltar directo.
  final Map<String, int> _letterOffsets = {};
  List<_ContactRow> _rows = [];

  static const _roleFilters = [
    (null, 'Todos'),
    ('owner', 'Propietarios'),
    ('buyer', 'Compradores'),
    ('contract', 'Con Contratos'),
    ('company', 'Empresas'),
    ('agency', 'Agencias aliadas'),
  ];

  @override
  void initState() {
    super.initState();
    _service = ContactService(context.read<AuthService>().odoo);
    _load();
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final result = await _service.list(
        searchText: _searchCtrl.text,
        role: _roleFilter,
      );
      if (mounted) {
        setState(() {
          _contacts = result;
          _buildRows();
        });
      }
    } catch (e) {
      if (mounted)
        setState(() => _error = 'No se pudieron cargar los contactos.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  /// Aplana contactos + encabezados de letra en una sola lista, guardando
  /// dónde empieza cada letra para el salto del índice lateral.
  void _buildRows() {
    _rows = [];
    _letterOffsets.clear();
    String? currentLetter;
    for (final c in _contacts) {
      final letter = _letterOf(c.name);
      if (letter != currentLetter) {
        currentLetter = letter;
        _letterOffsets[letter] = _rows.length;
        _rows.add(_ContactRow.header(letter));
      }
      _rows.add(_ContactRow.contact(c));
    }
  }

  String _letterOf(String name) {
    final trimmed = name.trim();
    if (trimmed.isEmpty) return '#';
    final first = trimmed[0].toUpperCase();
    return RegExp(r'[A-ZÑ]').hasMatch(first) ? first : '#';
  }

  void _jumpToLetter(String letter) {
    final index = _letterOffsets[letter];
    if (index == null || !_scrollController.hasClients) return;
    // Alto aproximado: encabezado 34, fila 68. Suficiente para caer en la
    // sección; el usuario ajusta con el dedo desde ahí.
    double offset = 0;
    for (int i = 0; i < index; i++) {
      offset += _rows[i].isHeader ? 34 : 68;
    }
    _scrollController.animateTo(
      offset.clamp(0, _scrollController.position.maxScrollExtent),
      duration: const Duration(milliseconds: 250),
      curve: Curves.easeOutCubic,
    );
  }

  Future<void> _openCreate() async {
    final saved = await Navigator.of(
      context,
    ).push<bool>(MaterialPageRoute(builder: (_) => const ContactFormScreen()));
    if (saved == true) _load();
  }

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.of(context);
    return Scaffold(
      floatingActionButton: Padding(
        padding: const EdgeInsets.only(bottom: 74),
        child: FloatingActionButton.small(
          heroTag: null,
          onPressed: _openCreate,
          backgroundColor: const Color(0xFFD81F26),
          elevation: 4,
          tooltip: 'Nuevo Contacto',
          child: const Icon(
            Icons.person_add_alt_1_rounded,
            color: Colors.white,
            size: 20,
          ),
        ),
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _searchCtrl,
                    decoration: InputDecoration(
                      hintText: 'Buscar por nombre, teléfono o email...',
                      prefixIcon: const Icon(Icons.search_rounded),
                      suffixIcon: _searchCtrl.text.isNotEmpty
                          ? IconButton(
                              icon: const Icon(Icons.close_rounded),
                              onPressed: () {
                                _searchCtrl.clear();
                                _load();
                              },
                            )
                          : null,
                    ),
                    onSubmitted: (_) => _load(),
                  ),
                ),
                const SizedBox(width: 8),
                Tooltip(
                  message: 'Nuevo Contacto',
                  child: Material(
                    color: const Color(0xFFD81F26),
                    borderRadius: BorderRadius.circular(14),
                    child: InkWell(
                      borderRadius: BorderRadius.circular(14),
                      onTap: _openCreate,
                      child: Container(
                        width: 44,
                        height: 44,
                        alignment: Alignment.center,
                        child: const Icon(
                          Icons.person_add_alt_1_rounded,
                          color: Colors.white,
                          size: 20,
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
          ChoiceChipRow(
            options: _roleFilters,
            value: _roleFilter,
            onChanged: (v) {
              setState(() => _roleFilter = v);
              _load();
            },
          ),
          if (!_loading && _error == null)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
              child: Row(
                children: [
                  Text(
                    '${_contacts.length} contactos',
                    style: TextStyle(
                      fontSize: 12,
                      color: colors.mutedLight,
                    ),
                  ),
                ],
              ),
            ),
          const SizedBox(height: 6),
          Expanded(
            child: RefreshIndicator(onRefresh: _load, child: _buildBody(colors)),
          ),
        ],
      ),
    );
  }

  Widget _buildBody(AppPalette colors) {
    if (_loading) return const SkeletonList();
    if (_error != null) {
      return MessageView(
        icon: Icons.error_outline,
        message: _error!,
        onRetry: _load,
      );
    }
    if (_contacts.isEmpty) {
      return const MessageView(
        icon: Icons.people_outline,
        message: 'No se encontraron contactos.',
      );
    }

    final letters = _letterOffsets.keys.toList();
    return Row(
      children: [
        Expanded(
          child: ListView.builder(
            controller: _scrollController,
            padding: const EdgeInsets.only(bottom: 90),
            itemCount: _rows.length,
            itemBuilder: (context, i) {
              final row = _rows[i];
              if (row.isHeader) {
                return Container(
                  height: 34,
                  color: colors.background,
                  padding: const EdgeInsets.symmetric(horizontal: 18),
                  alignment: Alignment.centerLeft,
                  child: Text(
                    row.letter!,
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 13,
                      color: colors.mutedLight,
                    ),
                  ),
                );
              }
              return _ContactTile(contact: row.contact!, onChanged: _load);
            },
          ),
        ),
        // Índice A-Z lateral
        if (letters.length > 3)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 8),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: letters
                  .map(
                    (l) => GestureDetector(
                      onTap: () => _jumpToLetter(l),
                      behavior: HitTestBehavior.opaque,
                      child: Padding(
                        padding: const EdgeInsets.symmetric(
                          vertical: 1.5,
                          horizontal: 4,
                        ),
                        child: Text(
                          l,
                          style: TextStyle(
                            fontSize: 10.5,
                            fontWeight: FontWeight.w700,
                            color: colors.navy,
                          ),
                        ),
                      ),
                    ),
                  )
                  .toList(),
            ),
          ),
      ],
    );
  }
}

/// Fila de la lista aplanada: o un encabezado de letra, o un contacto.
class _ContactRow {
  final String? letter;
  final Contact? contact;
  const _ContactRow.header(this.letter) : contact = null;
  const _ContactRow.contact(this.contact) : letter = null;
  bool get isHeader => letter != null;
}

class _ContactTile extends StatelessWidget {
  final Contact contact;
  final VoidCallback onChanged;
  const _ContactTile({required this.contact, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colors = AppColors.of(context);
    final phone = contact.bestPhone;

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 5),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1E1A3E) : Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: isDark ? Colors.white12 : const Color(0xFFE2E8F0),
        ),
        boxShadow: softShadow(opacity: isDark ? 0.2 : 0.035, isDark: isDark),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(18),
          onTap: () => Navigator.of(context)
              .push(
                MaterialPageRoute(
                  builder: (_) => ContactDetailScreen(contactId: contact.id),
                ),
              )
              .then((_) => onChanged()),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              children: [
                InitialsAvatar(
                  text: contact.name,
                  size: 44,
                  color: contact.roleColor(colors),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        contact.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 14.5,
                          letterSpacing: -0.2,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        [
                          contact.roleLabel,
                          if (contact.city.isNotEmpty) contact.city,
                        ].join(' · '),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 12,
                          color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                        ),
                      ),
                    ],
                  ),
                ),
                if (phone.isNotEmpty) ...[
                  Material(
                    color: isDark ? const Color(0xFF28244E) : const Color(0xFFF1F5F9),
                    borderRadius: BorderRadius.circular(10),
                    child: InkWell(
                      borderRadius: BorderRadius.circular(10),
                      onTap: () => launchUrl(
                        Uri.parse('tel:$phone'),
                        mode: LaunchMode.externalApplication,
                      ),
                      child: Container(
                        width: 34,
                        height: 34,
                        alignment: Alignment.center,
                        child: Icon(
                          Icons.phone_outlined,
                          color: isDark ? Colors.white70 : const Color(0xFF334155),
                          size: 16,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 6),
                  Material(
                    color: const Color(0xFF25D366),
                    borderRadius: BorderRadius.circular(10),
                    child: InkWell(
                      borderRadius: BorderRadius.circular(10),
                      onTap: () {
                        final clean = phone.replaceAll(RegExp(r'[^0-9]'), '');
                        final full = clean.startsWith('0')
                            ? '593${clean.substring(1)}'
                            : clean;
                        launchUrl(
                          Uri.parse('https://wa.me/$full'),
                          mode: LaunchMode.externalApplication,
                        );
                      },
                      child: Container(
                        width: 34,
                        height: 34,
                        alignment: Alignment.center,
                        child: const Icon(
                          Icons.chat_bubble_rounded,
                          color: Colors.white,
                          size: 16,
                        ),
                      ),
                    ),
                  ),
                ],
                if (contact.isPropertyOwner && phone.isEmpty)
                  AppBadge(label: 'Propietario', color: colors.navy),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
