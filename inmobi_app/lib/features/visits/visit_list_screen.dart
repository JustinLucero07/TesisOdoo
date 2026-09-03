import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import 'package:table_calendar/table_calendar.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api/odoo_client.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/phone_utils.dart';
import '../../core/widgets/app_badge.dart';
import '../../core/widgets/glass_nav_bar.dart';
import '../../core/widgets/motion.dart';
import '../../core/widgets/skeleton.dart';
import '../../core/widgets/states.dart';
import '../auth/auth_service.dart';
import 'visit_detail_screen.dart';
import 'visit_form_screen.dart';
import 'visit_model.dart';
import 'visit_service.dart';

class _AdvisorItem {
  final int id;
  final String name;
  const _AdvisorItem(this.id, this.name);
}

class VisitListScreen extends StatefulWidget {
  const VisitListScreen({super.key});

  @override
  State<VisitListScreen> createState() => _VisitListScreenState();
}

class _VisitListScreenState extends State<VisitListScreen> {
  late final OdooClient _odoo;
  late final VisitService _service;
  DateTime _selectedDay = DateTime.now();
  DateTime _focusedDay = DateTime.now();
  final CalendarFormat _calendarFormat = CalendarFormat.month;
  String? _typeFilter;
  String? _visitStateFilter;
  String? _visitResultFilter;

  // Filtro de Asesor: null = todos, 0 = mis citas, ID = asesor específico
  int? _selectedAdvisorId;
  List<_AdvisorItem> _advisors = [];

  Map<DateTime, List<Visit>> _monthVisits = {};
  bool _loading = true;
  String? _error;

  int get _activeVisitFilterCount {
    int count = 0;
    if (_visitStateFilter != null) count++;
    if (_visitResultFilter != null) count++;
    return count;
  }

  static const _typeFilters = [
    (null, 'Todas', Icons.calendar_view_day_rounded),
    ('visit', 'Visitas', Icons.home_work_outlined),
    ('meeting', 'Reuniones', Icons.groups_outlined),
    ('call', 'Llamadas', Icons.phone_in_talk_outlined),
    ('signing', 'Firmas', Icons.draw_outlined),
  ];

  DateTime _dayKey(DateTime d) => DateTime(d.year, d.month, d.day);

  String get _currentAdvisorName {
    final currentUserName = context.read<AuthService>().userName ?? 'Asesor';
    if (_selectedAdvisorId == 0) return currentUserName;
    if (_selectedAdvisorId == null) return 'Todos los asesores';
    final found = _advisors.where((a) => a.id == _selectedAdvisorId).firstOrNull;
    return found?.name ?? currentUserName;
  }

  String get _typeFilterLabel {
    final found = _typeFilters.where((t) => t.$1 == _typeFilter).firstOrNull;
    return found?.$2 ?? 'Todas';
  }

  List<Visit> get _visitsOfSelectedDay {
    final all = _monthVisits[_dayKey(_selectedDay)] ?? const [];
    final currentUid = _odoo.userId;

    return all.where((v) {
      if (_typeFilter != null && v.appointmentType != _typeFilter) {
        return false;
      }
      if (_visitStateFilter != null && v.visitState != _visitStateFilter) {
        return false;
      }
      if (_visitResultFilter != null && v.visitResult != _visitResultFilter) {
        return false;
      }
      if (_selectedAdvisorId == 0) {
        if (currentUid != null && v.userId != currentUid) return false;
      } else if (_selectedAdvisorId != null && _selectedAdvisorId! > 0) {
        if (v.userId != _selectedAdvisorId) return false;
      }
      return true;
    }).toList();
  }

  @override
  void initState() {
    super.initState();
    _odoo = context.read<AuthService>().odoo;
    _service = VisitService(_odoo);
    _selectedAdvisorId = 0; // Por defecto: "Mis citas"
    _loadAdvisors();
    _loadMonth(_focusedDay);
  }

  Future<void> _loadAdvisors() async {
    try {
      final rows = await _odoo.searchRead(
        model: 'res.users',
        domain: [
          ['share', '=', false],
        ],
        fields: ['name'],
        order: 'name asc',
        limit: 50,
      );
      if (mounted) {
        setState(() {
          _advisors = rows
              .map((r) => _AdvisorItem(r['id'] as int, (r['name'] ?? '').toString()))
              .where((a) => a.name.isNotEmpty)
              .toList();
        });
      }
    } catch (_) {
      // Silencioso
    }
  }

  Future<void> _loadMonth(DateTime month) async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final from = DateTime(
        month.year,
        month.month,
        1,
      ).subtract(const Duration(days: 7));
      final to = DateTime(
        month.year,
        month.month + 1,
        1,
      ).add(const Duration(days: 7));
      final visits = await _service.listByRange(from, to);
      final map = <DateTime, List<Visit>>{};
      for (final v in visits) {
        map.putIfAbsent(_dayKey(v.start), () => []).add(v);
      }
      if (mounted) setState(() => _monthVisits = map);
      unawaited(VisitService.scheduleNotifications(visits, currentUserId: _odoo.userId));
    } catch (e) {
      if (mounted) setState(() => _error = 'No se pudo cargar la agenda.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _openCreate() async {
    final saved = await Navigator.of(
      context,
    ).push<bool>(MaterialPageRoute(builder: (_) => const VisitFormScreen()));
    if (saved == true) _loadMonth(_focusedDay);
  }

  void _showAdvisorPicker() {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colors = AppColors.of(context);
    showModalBottomSheet(
      context: context,
      backgroundColor: isDark ? const Color(0xFF1E293B) : Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return Material(
          color: Colors.transparent,
          child: SafeArea(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Filtrar por Asesor',
                        style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800),
                      ),
                      IconButton(
                        icon: const Icon(Icons.close_rounded, size: 20),
                        onPressed: () => Navigator.pop(ctx),
                      ),
                    ],
                  ),
                ),
                const Divider(height: 1),
                ListTile(
                  leading: Icon(Icons.person_rounded, color: colors.navy),
                  title: const Text('Mis citas', style: TextStyle(fontWeight: FontWeight.w700)),
                  selected: _selectedAdvisorId == 0,
                  selectedTileColor: colors.navy.withValues(alpha: 0.08),
                  onTap: () {
                    setState(() => _selectedAdvisorId = 0);
                    Navigator.pop(ctx);
                  },
                ),
                ListTile(
                  leading: Icon(Icons.groups_rounded, color: colors.navy),
                  title: const Text('Todos los asesores', style: TextStyle(fontWeight: FontWeight.w700)),
                  selected: _selectedAdvisorId == null,
                  selectedTileColor: colors.navy.withValues(alpha: 0.08),
                  onTap: () {
                    setState(() => _selectedAdvisorId = null);
                    Navigator.pop(ctx);
                  },
                ),
                if (_advisors.isNotEmpty) const Divider(height: 1),
                ..._advisors.map((adv) {
                  return ListTile(
                    leading: const Icon(Icons.person_outline_rounded),
                    title: Text(adv.name),
                    selected: _selectedAdvisorId == adv.id,
                    selectedTileColor: colors.navy.withValues(alpha: 0.08),
                    onTap: () {
                      setState(() => _selectedAdvisorId = adv.id);
                      Navigator.pop(ctx);
                    },
                  );
                }),
                const SizedBox(height: 12),
              ],
            ),
          ),
        );
      },
    );
  }

  void _showTypePicker() {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colors = AppColors.of(context);
    showModalBottomSheet(
      context: context,
      backgroundColor: isDark ? const Color(0xFF1E293B) : Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return Material(
          color: Colors.transparent,
          child: SafeArea(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Tipo de Actividad',
                        style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800),
                      ),
                      IconButton(
                        icon: const Icon(Icons.close_rounded, size: 20),
                        onPressed: () => Navigator.pop(ctx),
                      ),
                    ],
                  ),
                ),
                const Divider(height: 1),
                ..._typeFilters.map((tf) {
                  final (type, label, icon) = tf;
                  final selected = _typeFilter == type;
                  return ListTile(
                    leading: Icon(icon, color: selected ? colors.navy : null),
                    title: Text(
                      label,
                      style: TextStyle(
                        fontWeight: selected ? FontWeight.w800 : FontWeight.w500,
                        color: selected ? colors.navy : null,
                      ),
                    ),
                    selected: selected,
                    selectedTileColor: colors.navy.withValues(alpha: 0.08),
                    onTap: () {
                      setState(() => _typeFilter = type);
                      Navigator.pop(ctx);
                    },
                  );
                }),
                const SizedBox(height: 12),
              ],
            ),
          ),
        );
      },
    );
  }

  void _showAdvancedVisitFilters() {
    HapticFeedback.lightImpact();
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => _VisitFilterSheet(
        visitState: _visitStateFilter,
        visitResult: _visitResultFilter,
        onApply: (state, result) {
          setState(() {
            _visitStateFilter = state;
            _visitResultFilter = result;
          });
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colors = AppColors.of(context);

    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF0F172A) : Colors.white,
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Header Azul Vibrante (Idéntico a la captura) ──
          Container(
            width: double.infinity,
            padding: EdgeInsets.only(
              top: MediaQuery.of(context).padding.top + 8,
              left: 18,
              right: 8,
              bottom: 14,
            ),
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                colors: [Color(0xFF1E1A3E), Color(0xFF28235D)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Agenda',
                  style: TextStyle(
                    fontSize: 26,
                    fontWeight: FontWeight.w800,
                    color: Colors.white,
                    letterSpacing: -0.5,
                  ),
                ),
                IconButton(
                  onPressed: _openCreate,
                  icon: const Icon(
                    Icons.add,
                    color: Color(0xFFFFB800), // Dorado/amarillo vibrante
                    size: 30,
                  ),
                  tooltip: 'Nueva Cita',
                ),
              ],
            ),
          ),

          // ── Sub-header: Selector de Asesor y Filtro Tipo / Estado ──
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF1E293B) : Colors.white,
              border: Border(
                bottom: BorderSide(
                  color: isDark ? const Color(0xFF334155) : const Color(0xFFE2E8F0),
                  width: 1,
                ),
              ),
            ),
            child: Row(
              children: [
                InkWell(
                  onTap: _showAdvisorPicker,
                  borderRadius: BorderRadius.circular(8),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 2, horizontal: 4),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          'De: ',
                          style: TextStyle(
                            fontSize: 14,
                            color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        Text(
                          _currentAdvisorName,
                          style: TextStyle(
                            fontSize: 14,
                            color: colors.navy,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const Spacer(),
                InkWell(
                  onTap: _showTypePicker,
                  borderRadius: BorderRadius.circular(8),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 2, horizontal: 4),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          '| ',
                          style: TextStyle(
                            color: isDark ? Colors.white24 : const Color(0xFFCBD5E1),
                            fontSize: 16,
                          ),
                        ),
                        Icon(
                          Icons.filter_list_rounded,
                          size: 18,
                          color: colors.navy,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          _typeFilterLabel,
                          style: TextStyle(
                            fontSize: 14,
                            color: colors.navy,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                InkWell(
                  onTap: _showAdvancedVisitFilters,
                  borderRadius: BorderRadius.circular(8),
                  child: Stack(
                    clipBehavior: Clip.none,
                    children: [
                      Container(
                        padding: const EdgeInsets.all(6),
                        decoration: BoxDecoration(
                          color: _activeVisitFilterCount > 0
                              ? const Color(0xFF28235D)
                              : (isDark ? const Color(0xFF334155) : const Color(0xFFF1F5F9)),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Icon(
                          Icons.tune_rounded,
                          size: 18,
                          color: _activeVisitFilterCount > 0 ? Colors.white : colors.navy,
                        ),
                      ),
                      if (_activeVisitFilterCount > 0)
                        Positioned(
                          top: -3,
                          right: -3,
                          child: Container(
                            padding: const EdgeInsets.all(4),
                            decoration: const BoxDecoration(
                              color: Color(0xFFD81F26),
                              shape: BoxShape.circle,
                            ),
                            child: Text(
                              '$_activeVisitFilterCount',
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 9,
                                fontWeight: FontWeight.w800,
                                height: 1,
                              ),
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // ── Calendario Mensual Limpio en Blanco ──
          Container(
            color: isDark ? const Color(0xFF1E293B) : Colors.white,
            padding: const EdgeInsets.only(bottom: 8),
            child: TableCalendar<Visit>(
              locale: 'es_EC',
              firstDay: DateTime.now().subtract(const Duration(days: 365)),
              lastDay: DateTime.now().add(const Duration(days: 365)),
              focusedDay: _focusedDay,
              currentDay: DateTime.now(),
              rowHeight: 38,
              daysOfWeekHeight: 24,
              selectedDayPredicate: (day) => isSameDay(_selectedDay, day),
              calendarFormat: _calendarFormat,
              availableCalendarFormats: const {
                CalendarFormat.month: 'Mes',
              },
              eventLoader: (day) => _monthVisits[_dayKey(day)] ?? const [],
              onDaySelected: (selected, focused) {
                setState(() {
                  _selectedDay = selected;
                  _focusedDay = focused;
                });
              },
              onPageChanged: (focused) {
                _focusedDay = focused;
                _loadMonth(focused);
              },
              headerStyle: HeaderStyle(
                formatButtonVisible: false,
                titleCentered: true,
                headerPadding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
                titleTextStyle: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w800,
                  color: isDark ? Colors.white : const Color(0xFF0F172A),
                ),
                leftChevronIcon: Icon(
                  Icons.arrow_circle_left_outlined,
                  size: 24,
                  color: isDark ? Colors.white70 : const Color(0xFF64748B),
                ),
                rightChevronIcon: Icon(
                  Icons.arrow_circle_right_outlined,
                  size: 24,
                  color: isDark ? Colors.white70 : const Color(0xFF64748B),
                ),
              ),
              daysOfWeekStyle: const DaysOfWeekStyle(
                weekdayStyle: TextStyle(
                  fontSize: 12,
                  color: Color(0xFF94A3B8),
                  fontWeight: FontWeight.w600,
                ),
                weekendStyle: TextStyle(
                  fontSize: 12,
                  color: Color(0xFF94A3B8),
                  fontWeight: FontWeight.w600,
                ),
              ),
              calendarStyle: CalendarStyle(
                outsideDaysVisible: true,
                outsideTextStyle: const TextStyle(
                  fontSize: 13.5,
                  color: Color(0xFFCBD5E1),
                ),
                defaultTextStyle: TextStyle(
                  fontSize: 13.5,
                  fontWeight: FontWeight.w600,
                  color: isDark ? Colors.white : const Color(0xFF0F172A),
                ),
                weekendTextStyle: TextStyle(
                  fontSize: 13.5,
                  fontWeight: FontWeight.w600,
                  color: isDark ? Colors.white70 : const Color(0xFF334155),
                ),
                todayDecoration: const BoxDecoration(
                  color: Colors.transparent,
                ),
                todayTextStyle: TextStyle(
                  color: colors.navy,
                  fontWeight: FontWeight.w900,
                  fontSize: 14,
                ),
                selectedDecoration: BoxDecoration(
                  color: colors.navy,
                  shape: BoxShape.circle,
                ),
                selectedTextStyle: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                  fontSize: 13.5,
                ),
                markerDecoration: const BoxDecoration(
                  color: Color(0xFFEF4444),
                  shape: BoxShape.circle,
                ),
                markersMaxCount: 3,
                markerSize: 5,
                markerMargin: const EdgeInsets.only(top: 2),
              ),
            ),
          ),

          // Línea divisoria
          Container(
            height: 1,
            color: isDark ? const Color(0xFF334155) : const Color(0xFFE2E8F0),
          ),

          // ── Sección Tareas del Día (Cabecera estilo HOY · X CITAS) ──
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 10),
            child: Builder(
              builder: (context) {
                final visits = _visitsOfSelectedDay;
                final count = visits.length;
                final now = DateTime.now();
                final isToday = _selectedDay.year == now.year &&
                    _selectedDay.month == now.month &&
                    _selectedDay.day == now.day;
                final countLabel = '$count ${count == 1 ? "CITA" : "CITAS"}';
                final headerText = isToday
                    ? 'HOY · $countLabel'
                    : '${DateFormat('d \'DE\' MMMM', 'es_EC').format(_selectedDay).toUpperCase()} · $countLabel';

                return Text(
                  headerText,
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.9,
                    color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                  ),
                );
              },
            ),
          ),

          // Lista de Eventos en Timeline o Estado Vacío
          Expanded(
            child: RefreshIndicator(
              onRefresh: () => _loadMonth(_focusedDay),
              child: _buildBody(isDark, colors),
            ),
          ),
        ],
      ),
    );
  }

  final Map<int, String> _partnerPhones = {};

  Future<String?> _getPartnerPhone(int partnerId) async {
    if (_partnerPhones.containsKey(partnerId)) {
      return _partnerPhones[partnerId];
    }
    try {
      final rows = await _odoo.searchRead(
        model: 'res.partner',
        domain: [
          ['id', '=', partnerId],
        ],
        fields: ['phone', 'mobile'],
        limit: 1,
      );
      if (rows.isNotEmpty) {
        final r = rows.first;
        final mobile = (r['mobile'] ?? '').toString().trim();
        final phone = (r['phone'] ?? '').toString().trim();
        final chosen = mobile.isNotEmpty ? mobile : phone;
        if (chosen.isNotEmpty) {
          _partnerPhones[partnerId] = chosen;
          return chosen;
        }
      }
    } catch (_) {}
    return null;
  }

  Future<void> _callClient(Visit v) async {
    HapticFeedback.selectionClick();
    String? phone;
    if (v.clientId != null) {
      phone = await _getPartnerPhone(v.clientId!);
    }
    if (phone != null && phone.isNotEmpty) {
      await PhoneUtils.call(phone);
      return;
    }
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            v.clientName.isNotEmpty
                ? '${v.clientName} no tiene teléfono registrado en Odoo.'
                : 'Esta cita no tiene un contacto con teléfono vinculado.',
          ),
        ),
      );
    }
  }

  Future<void> _openWhatsApp(Visit v, DateFormat timeFmt) async {
    HapticFeedback.selectionClick();
    String? phone;
    if (v.clientId != null) {
      phone = await _getPartnerPhone(v.clientId!);
    }
    final clientName = v.clientName.isNotEmpty ? v.clientName : 'Estimado/a';
    final propName = v.propertyName.isNotEmpty ? v.propertyName : v.name;
    final timeStr = timeFmt.format(v.start);
    final msg =
        'Hola $clientName, te saludo de Inmobi Inmobiliaria respecto a $propName programada para hoy a las $timeStr.';

    if (phone != null && phone.isNotEmpty) {
      await PhoneUtils.whatsapp(phone, text: msg);
      return;
    }

    final uri = Uri.parse('https://wa.me/?text=${Uri.encodeComponent(msg)}');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } else {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No se pudo abrir WhatsApp.')),
        );
      }
    }
  }

  Future<void> _openLocation(Visit v) async {
    HapticFeedback.selectionClick();
    String query = v.location.trim();
    if (query.isEmpty && v.propertyName.isNotEmpty) {
      query = v.propertyName;
    }
    if (query.isEmpty) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Esta cita no tiene una dirección registrada.')),
        );
      }
      return;
    }

    final uri = Uri.parse(
      'https://www.google.com/maps/search/?api=1&query=${Uri.encodeComponent('$query Ecuador')}',
    );
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  static (Color bg, Color text, String label) _pillBadge(String type, bool isDark) {
    final t = type.toLowerCase().trim();
    if (t.contains('visita') || t == 'visit') {
      return isDark
          ? (const Color(0xFF1E3A8A).withValues(alpha: 0.45), const Color(0xFF93C5FD), 'Visita')
          : (const Color(0xFFEFF6FF), const Color(0xFF2563EB), 'Visita');
    }
    if (t.contains('avaluo') || t.contains('avalúo') || t == 'appraisal') {
      return isDark
          ? (const Color(0xFF78350F).withValues(alpha: 0.45), const Color(0xFFFCD34D), 'Avalúo')
          : (const Color(0xFFFEF3C7), const Color(0xFFD97706), 'Avalúo');
    }
    if (t.contains('firma') || t == 'signing') {
      return isDark
          ? (const Color(0xFF064E3B).withValues(alpha: 0.45), const Color(0xFF6EE7B7), 'Firma')
          : (const Color(0xFFECFDF5), const Color(0xFF059669), 'Firma');
    }
    if (t.contains('reunion') || t.contains('reunión') || t == 'meeting') {
      return isDark
          ? (const Color(0xFF581C87).withValues(alpha: 0.45), const Color(0xFFC4B5FD), 'Reunión')
          : (const Color(0xFFF3E8FF), const Color(0xFF7C3AED), 'Reunión');
    }
    if (t.contains('llamada') || t == 'call') {
      return isDark
          ? (const Color(0xFF14532D).withValues(alpha: 0.45), const Color(0xFF86EFAC), 'Llamada')
          : (const Color(0xFFF0FDF4), const Color(0xFF16A34A), 'Llamada');
    }
    return isDark
        ? (const Color(0xFF334155), const Color(0xFFCBD5E1), 'Cita')
        : (const Color(0xFFF1F5F9), const Color(0xFF475569), 'Cita');
  }

  static (String title, String subtitle) _extractTitles(Visit v) {
    final type = v.appointmentType.toLowerCase().trim();
    if ((type == 'visit' || type.contains('visita')) && v.clientName.isNotEmpty) {
      final title = v.clientName;
      final subtitle = v.propertyName.isNotEmpty
          ? v.propertyName
          : (v.location.isNotEmpty ? v.location : v.name);
      return (title, subtitle);
    }
    if (v.propertyName.isNotEmpty) {
      final title = v.propertyName;
      final subtitle = v.clientName.isNotEmpty
          ? 'Con: ${v.clientName}'
          : (v.location.isNotEmpty ? v.location : v.name);
      return (title, subtitle);
    }
    final title = v.name;
    final subtitle = v.clientName.isNotEmpty
        ? 'Con: ${v.clientName}'
        : (v.location.isNotEmpty ? v.location : '');
    return (title, subtitle);
  }

  Widget _buildBody(bool isDark, AppPalette colors) {
    if (_loading && _monthVisits.isEmpty) return const SkeletonList();
    if (_error != null) {
      return MessageView(
        icon: Icons.error_outline,
        message: _error!,
        onRetry: () => _loadMonth(_focusedDay),
      );
    }
    final visits = _visitsOfSelectedDay;
    if (visits.isEmpty) {
      return ListView(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 30),
        children: [
          Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const SizedBox(height: 16),
                Icon(
                  Icons.calendar_today_outlined,
                  size: 48,
                  color: isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8),
                ),
                const SizedBox(height: 14),
                Text(
                  '$_currentAdvisorName aún no tiene eventos registrados en este día',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 13.5,
                    fontWeight: FontWeight.w500,
                    color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                    height: 1.4,
                  ),
                ),
                const SizedBox(height: 16),
                OutlinedButton.icon(
                  onPressed: () {
                    Navigator.of(context)
                        .push(
                          MaterialPageRoute(
                            builder: (_) => VisitFormScreen(
                              initialDate: _selectedDay,
                            ),
                          ),
                        )
                        .then((_) => _loadMonth(_focusedDay));
                  },
                  icon: const Icon(Icons.add_rounded, size: 18),
                  label: const Text('Agendar Cita'),
                ),
              ],
            ),
          ),
        ],
      );
    }

    final timeFmt = DateFormat.Hm('es_EC');

    return ListView.builder(
      padding: const EdgeInsets.fromLTRB(
        16,
        4,
        16,
        GlassNavBar.reservedHeight + 8,
      ),
      itemCount: visits.length,
      itemBuilder: (context, i) {
        final v = visits[i];
        final isLast = i == visits.length - 1;
        return FadeSlideIn(
          index: i,
          child: _buildTimelineItem(v, timeFmt, isLast, isDark, colors),
        );
      },
    );
  }

  Widget _buildTimelineItem(
    Visit v,
    DateFormat timeFmt,
    bool isLast,
    bool isDark,
    AppPalette colors,
  ) {
    final pill = _pillBadge(v.appointmentType, isDark);
    final titles = _extractTitles(v);
    final timeStr = timeFmt.format(v.start);

    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // ── Columna de Hora ──
          SizedBox(
            width: 48,
            child: Padding(
              padding: const EdgeInsets.only(top: 2),
              child: Text(
                timeStr,
                style: TextStyle(
                  fontWeight: FontWeight.w800,
                  fontSize: 13.5,
                  color: isDark ? const Color(0xFFCBD5E1) : const Color(0xFF1E293B),
                ),
              ),
            ),
          ),

          // ── Nodo del Timeline y Línea vertical ──
          SizedBox(
            width: 22,
            child: Column(
              children: [
                Container(
                  margin: const EdgeInsets.only(top: 5),
                  width: 9,
                  height: 9,
                  decoration: BoxDecoration(
                    color: isDark ? const Color(0xFF818CF8) : const Color(0xFF1E1B4B),
                    shape: BoxShape.circle,
                  ),
                ),
                if (!isLast)
                  Expanded(
                    child: Container(
                      width: 1.5,
                      margin: const EdgeInsets.symmetric(vertical: 4),
                      color: isDark ? const Color(0xFF334155) : const Color(0xFFE2E8F0),
                    ),
                  ),
              ],
            ),
          ),

          const SizedBox(width: 6),

          // ── Tarjeta de la Cita (Diseño de la imagen 1) ──
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: Container(
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF1E293B) : Colors.white,
                  borderRadius: BorderRadius.circular(18),
                  border: Border.all(
                    color: isDark ? const Color(0xFF334155) : const Color(0xFFE2E8F0),
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: isDark ? 0.25 : 0.035),
                      blurRadius: 10,
                      offset: const Offset(0, 3),
                    ),
                  ],
                ),
                child: Material(
                  color: Colors.transparent,
                  child: InkWell(
                    borderRadius: BorderRadius.circular(18),
                    onTap: () => Navigator.of(context)
                        .push(
                          MaterialPageRoute(
                            builder: (_) => VisitDetailScreen(visitId: v.id),
                          ),
                        )
                        .then((_) => _loadMonth(_focusedDay)),
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // Badge Pill (Visita, Avalúo, Firma, etc.)
                          Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 10,
                                  vertical: 3.5,
                                ),
                                decoration: BoxDecoration(
                                  color: pill.$1,
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: Text(
                                  pill.$3,
                                  style: TextStyle(
                                    color: pill.$2,
                                    fontWeight: FontWeight.w700,
                                    fontSize: 11.5,
                                  ),
                                ),
                              ),
                              const Spacer(),
                              if (v.visitState != 'scheduled')
                                AppBadge(
                                  label: VisitStateStyle.label(v.visitState),
                                  color: VisitStateStyle.color(v.visitState, colors),
                                ),
                            ],
                          ),

                          const SizedBox(height: 10),

                          // Título Principal
                          Text(
                            titles.$1,
                            style: TextStyle(
                              fontWeight: FontWeight.w800,
                              fontSize: 15.5,
                              color: isDark ? Colors.white : const Color(0xFF0F172A),
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),

                          // Subtítulo
                          if (titles.$2.isNotEmpty) ...[
                            const SizedBox(height: 3),
                            Text(
                              titles.$2,
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w500,
                                color: isDark
                                    ? const Color(0xFF94A3B8)
                                    : const Color(0xFF64748B),
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ],

                          const SizedBox(height: 12),

                          // ── Botones de Acción Rápida (Llamada, WhatsApp, Ubicación) ──
                          Row(
                            children: [
                              // Botón Teléfono
                              _ActionCircleButton(
                                icon: Icons.phone_outlined,
                                bgColor: isDark
                                    ? const Color(0xFF28244E)
                                    : const Color(0xFFF1F5F9),
                                iconColor: isDark
                                    ? Colors.white70
                                    : const Color(0xFF334155),
                                onTap: () => _callClient(v),
                              ),
                              const SizedBox(width: 8),

                              // Botón WhatsApp (Verde)
                              _ActionCircleButton(
                                icon: Icons.chat_bubble_rounded,
                                bgColor: const Color(0xFF25D366),
                                iconColor: Colors.white,
                                onTap: () => _openWhatsApp(v, timeFmt),
                              ),
                              const SizedBox(width: 8),

                              // Botón Ubicación / Mapa
                              _ActionCircleButton(
                                icon: Icons.location_on_outlined,
                                bgColor: isDark
                                    ? const Color(0xFF28244E)
                                    : const Color(0xFFF1F5F9),
                                iconColor: isDark
                                    ? Colors.white70
                                    : const Color(0xFF334155),
                                onTap: () => _openLocation(v),
                              ),
                            ],
                          ),
                        ],
                      ),
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

/// Botón de acción rápida circular / píldora para la tarjeta de cita
class _ActionCircleButton extends StatelessWidget {
  final IconData icon;
  final Color bgColor;
  final Color iconColor;
  final VoidCallback onTap;

  const _ActionCircleButton({
    required this.icon,
    required this.bgColor,
    required this.iconColor,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: bgColor,
      borderRadius: BorderRadius.circular(10),
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: onTap,
        child: Container(
          width: 36,
          height: 36,
          alignment: Alignment.center,
          child: Icon(icon, color: iconColor, size: 18),
        ),
      ),
    );
  }
}

/// Hoja modal de filtros avanzados para la Agenda de Citas
class _VisitFilterSheet extends StatefulWidget {
  final String? visitState;
  final String? visitResult;
  final Function(String?, String?) onApply;

  const _VisitFilterSheet({
    required this.visitState,
    required this.visitResult,
    required this.onApply,
  });

  @override
  State<_VisitFilterSheet> createState() => _VisitFilterSheetState();
}

class _VisitFilterSheetState extends State<_VisitFilterSheet> {
  String? _visitState;
  String? _visitResult;

  static const _stateOptions = [
    (null, 'Todos'),
    ('scheduled', 'Programadas'),
    ('done', 'Realizadas'),
    ('cancelled', 'Canceladas'),
  ];

  static const _resultOptions = [
    (null, 'Cualquiera'),
    ('interested', 'Muy Interesado'),
    ('offer_made', 'Con Oferta'),
    ('follow_up', 'En Seguimiento'),
    ('not_interested', 'No Interesado'),
  ];

  @override
  void initState() {
    super.initState();
    _visitState = widget.visitState;
    _visitResult = widget.visitResult;
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Container(
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF14112E) : Colors.white,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
      ),
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      child: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 10),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              // Manija
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: isDark ? Colors.white24 : Colors.grey[300],
                    borderRadius: BorderRadius.circular(10),
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Cabecera
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Filtros de Agenda',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  TextButton(
                    onPressed: () {
                      setState(() {
                        _visitState = null;
                        _visitResult = null;
                      });
                    },
                    child: const Text(
                      'Restablecer',
                      style: TextStyle(
                        color: Color(0xFFD81F26),
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ),
              const Divider(height: 20),

              // 1. Estado de la Cita
              const Text(
                'Estado de la Cita',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: _stateOptions.map((opt) {
                  final (val, label) = opt;
                  final selected = _visitState == val;
                  return _VisitFilterChip(
                    label: label,
                    selected: selected,
                    onTap: () => setState(() => _visitState = val),
                  );
                }).toList(),
              ),
              const SizedBox(height: 18),

              // 2. Nivel de Interés / Resultado
              const Text(
                'Interés / Resultado Comercial',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: _resultOptions.map((opt) {
                  final (val, label) = opt;
                  final selected = _visitResult == val;
                  return _VisitFilterChip(
                    label: label,
                    selected: selected,
                    onTap: () => setState(() => _visitResult = val),
                  );
                }).toList(),
              ),
              const SizedBox(height: 24),

              // Botón Aplicar
              SizedBox(
                width: double.infinity,
                height: 48,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF28235D),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14),
                    ),
                    elevation: 3,
                  ),
                  onPressed: () {
                    widget.onApply(_visitState, _visitResult);
                    Navigator.pop(context);
                  },
                  child: const Text(
                    'Aplicar Filtros',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w800,
                      color: Colors.white,
                      letterSpacing: 0.3,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _VisitFilterChip extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _VisitFilterChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: selected
              ? const Color(0xFF28235D)
              : (isDark ? const Color(0xFF1E1A3E) : const Color(0xFFF1F5F9)),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: selected
                ? const Color(0xFF28235D)
                : (isDark ? Colors.white12 : const Color(0xFFE2E8F0)),
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 12.5,
            fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
            color: selected
                ? Colors.white
                : (isDark ? Colors.white70 : const Color(0xFF334155)),
          ),
        ),
      ),
    );
  }
}
