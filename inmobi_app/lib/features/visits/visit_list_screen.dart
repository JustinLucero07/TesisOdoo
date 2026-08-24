import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import 'package:table_calendar/table_calendar.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api/odoo_client.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/app_badge.dart';
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
                  leading: const Icon(Icons.person_rounded, color: AppColors.navy),
                  title: const Text('Mis citas', style: TextStyle(fontWeight: FontWeight.w700)),
                  selected: _selectedAdvisorId == 0,
                  selectedTileColor: AppColors.navy.withValues(alpha: 0.08),
                  onTap: () {
                    setState(() => _selectedAdvisorId = 0);
                    Navigator.pop(ctx);
                  },
                ),
                ListTile(
                  leading: const Icon(Icons.groups_rounded, color: AppColors.navy),
                  title: const Text('Todos los asesores', style: TextStyle(fontWeight: FontWeight.w700)),
                  selected: _selectedAdvisorId == null,
                  selectedTileColor: AppColors.navy.withValues(alpha: 0.08),
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
                    selectedTileColor: AppColors.navy.withValues(alpha: 0.08),
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
                    leading: Icon(icon, color: selected ? AppColors.navy : null),
                    title: Text(
                      label,
                      style: TextStyle(
                        fontWeight: selected ? FontWeight.w800 : FontWeight.w500,
                        color: selected ? AppColors.navy : null,
                      ),
                    ),
                    selected: selected,
                    selectedTileColor: AppColors.navy.withValues(alpha: 0.08),
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
    final dayLabel = DateFormat("d 'de' MMMM", 'es_EC').format(_selectedDay);

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
                          style: const TextStyle(
                            fontSize: 14,
                            color: AppColors.navy,
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
                        const Icon(
                          Icons.filter_list_rounded,
                          size: 18,
                          color: AppColors.navy,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          _typeFilterLabel,
                          style: const TextStyle(
                            fontSize: 14,
                            color: AppColors.navy,
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
                          color: _activeVisitFilterCount > 0 ? Colors.white : AppColors.navy,
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
                todayTextStyle: const TextStyle(
                  color: AppColors.navy,
                  fontWeight: FontWeight.w900,
                  fontSize: 14,
                ),
                selectedDecoration: const BoxDecoration(
                  color: AppColors.navy,
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

          // ── Sección Tareas del Día ──
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 14, 18, 8),
            child: Text(
              'Tareas del $dayLabel',
              style: TextStyle(
                fontSize: 15.5,
                fontWeight: FontWeight.w800,
                color: isDark ? Colors.white : const Color(0xFF0F172A),
              ),
            ),
          ),

          // Lista de Eventos o Estado Vacío
          Expanded(
            child: RefreshIndicator(
              onRefresh: () => _loadMonth(_focusedDay),
              child: _buildBody(isDark),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBody(bool isDark) {
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
              ],
            ),
          ),
        ],
      );
    }

    final timeFmt = DateFormat.Hm('es_EC');
    final currentUid = _odoo.userId;

    return LayoutBuilder(
      builder: (context, constraints) {
        final w = constraints.maxWidth;
        final cols = w >= 720 ? 2 : 1;

        if (cols == 1) {
          return ListView.separated(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 100),
            itemCount: visits.length,
            separatorBuilder: (_, _) => const SizedBox(height: 10),
            itemBuilder: (context, i) => _buildVisitItem(visits[i], timeFmt, currentUid, isDark),
          );
        }

        return GridView.builder(
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 100),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 2,
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
            mainAxisExtent: 160,
          ),
          itemCount: visits.length,
          itemBuilder: (context, i) => _buildVisitItem(visits[i], timeFmt, currentUid, isDark),
        );
      },
    );
  }

  Widget _buildVisitItem(Visit v, DateFormat timeFmt, int? currentUid, bool isDark) {
    final typeColor = AppointmentTypeStyle.color(v.appointmentType);
    final isOtherAdvisor = v.userId != null && currentUid != null && v.userId != currentUid;

    return Dismissible(
      key: ValueKey('visit_${v.id}'),
      direction: DismissDirection.horizontal,
      confirmDismiss: (direction) async {
        HapticFeedback.mediumImpact();
        if (direction == DismissDirection.startToEnd) {
          final clientName = v.clientName.isNotEmpty ? v.clientName : 'Estimado/a';
          final propName = v.propertyName.isNotEmpty ? v.propertyName : 'su cita';
          final msg = Uri.encodeComponent('Hola $clientName, te saludo de Inmobi Inmobiliaria respecto a $propName agendada a las ${timeFmt.format(v.start)}.');
          final url = Uri.parse('https://wa.me/?text=$msg');
          if (await canLaunchUrl(url)) {
            await launchUrl(url, mode: LaunchMode.externalApplication);
          } else {
            if (mounted) {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('No se pudo abrir WhatsApp.')),
              );
            }
          }
        } else if (direction == DismissDirection.endToStart) {
          if (mounted) {
            Navigator.of(context)
                .push(
                  MaterialPageRoute(
                    builder: (_) => VisitDetailScreen(visitId: v.id),
                  ),
                )
                .then((_) => _loadMonth(_focusedDay));
          }
        }
        return false;
      },
      background: Container(
        alignment: Alignment.centerLeft,
        padding: const EdgeInsets.symmetric(horizontal: 20),
        decoration: BoxDecoration(
          color: const Color(0xFF25D366),
          borderRadius: BorderRadius.circular(16),
        ),
        child: const Row(
          children: [
            Icon(Icons.chat_bubble_outline_rounded, color: Colors.white, size: 22),
            SizedBox(width: 8),
            Text(
              'WhatsApp',
              style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 13),
            ),
          ],
        ),
      ),
      secondaryBackground: Container(
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.symmetric(horizontal: 20),
        decoration: BoxDecoration(
          color: const Color(0xFF28235D),
          borderRadius: BorderRadius.circular(16),
        ),
        child: const Row(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            Text(
              'Ver Detalle',
              style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 13),
            ),
            SizedBox(width: 8),
            Icon(Icons.arrow_forward_ios_rounded, color: Colors.white, size: 18),
          ],
        ),
      ),
      child: Container(
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF1E293B) : Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isDark ? const Color(0xFF334155) : const Color(0xFFE2E8F0),
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: isDark ? 0.2 : 0.03),
              blurRadius: 8,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: BorderRadius.circular(16),
            onTap: () => Navigator.of(context)
                .push(
                  MaterialPageRoute(
                    builder: (_) => VisitDetailScreen(visitId: v.id),
                  ),
                )
                .then((_) => _loadMonth(_focusedDay)),
            child: IntrinsicHeight(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Container(
                    width: 5,
                    decoration: BoxDecoration(
                      color: typeColor,
                      borderRadius: const BorderRadius.only(
                        topLeft: Radius.circular(16),
                        bottomLeft: Radius.circular(16),
                      ),
                    ),
                  ),
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                                decoration: BoxDecoration(
                                  color: typeColor.withValues(alpha: 0.1),
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: Text(
                                  timeFmt.format(v.start),
                                  style: TextStyle(
                                    fontWeight: FontWeight.w800,
                                    color: typeColor,
                                    fontSize: 11.5,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 8),
                              Text(
                                AppointmentTypeStyle.label(v.appointmentType),
                                style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w700,
                                  color: typeColor,
                                ),
                              ),
                              const Spacer(),
                              AppBadge(
                                label: VisitStateStyle.label(v.visitState),
                                color: VisitStateStyle.color(v.visitState),
                              ),
                            ],
                          ),
                          if (v.userName.isNotEmpty && isOtherAdvisor) ...[
                            const SizedBox(height: 6),
                            Text(
                              'Asesor: ${v.userName}',
                              style: const TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w700,
                                color: AppColors.navy,
                              ),
                            ),
                          ],
                          const SizedBox(height: 8),
                          Text(
                            v.propertyName.isNotEmpty ? v.propertyName : v.name,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontWeight: FontWeight.w800,
                              fontSize: 14.5,
                              height: 1.25,
                            ),
                          ),
                          if (v.clientName.isNotEmpty) ...[
                            const SizedBox(height: 6),
                            Row(
                              children: [
                                CircleAvatar(
                                  radius: 10,
                                  backgroundColor: AppColors.navy.withValues(alpha: 0.1),
                                  child: Text(
                                    v.clientName[0].toUpperCase(),
                                    style: const TextStyle(
                                      fontSize: 9.5,
                                      fontWeight: FontWeight.w800,
                                      color: AppColors.navy,
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 6),
                                Expanded(
                                  child: Text(
                                    v.clientName,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(
                                      fontSize: 12,
                                      fontWeight: FontWeight.w500,
                                      color: AppColors.muted,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ],
                          if (v.location.isNotEmpty) ...[
                            const SizedBox(height: 6),
                            Row(
                              children: [
                                const Icon(
                                  Icons.place_outlined,
                                  size: 13,
                                  color: AppColors.mutedLight,
                                ),
                                const SizedBox(width: 4),
                                Expanded(
                                  child: Text(
                                    v.location,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(
                                      fontSize: 11.5,
                                      color: AppColors.mutedLight,
                                    ),
                                  ),
                                ),
                                InkWell(
                                  borderRadius: BorderRadius.circular(6),
                                  onTap: () async {
                                    final uri = Uri.parse(
                                      'https://www.google.com/maps/search/?api=1&query=${Uri.encodeComponent('${v.location} Ecuador')}',
                                    );
                                    if (await canLaunchUrl(uri)) {
                                      await launchUrl(uri, mode: LaunchMode.externalApplication);
                                    }
                                  },
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: const Color(0xFFEF4444).withValues(alpha: 0.1),
                                      borderRadius: BorderRadius.circular(6),
                                    ),
                                    child: const Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Icon(Icons.navigation_rounded, size: 9, color: Color(0xFFEF4444)),
                                        SizedBox(width: 2),
                                        Text(
                                          'GPS',
                                          style: TextStyle(
                                            fontSize: 9,
                                            fontWeight: FontWeight.w800,
                                            color: Color(0xFFEF4444),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
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
