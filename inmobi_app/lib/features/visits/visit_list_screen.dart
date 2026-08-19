import 'dart:async';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import 'package:table_calendar/table_calendar.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/app_badge.dart';
import '../../core/widgets/choice_chip_row.dart';
import '../../core/widgets/states.dart';
import '../../core/widgets/skeleton.dart';
import '../auth/auth_service.dart';
import 'visit_detail_screen.dart';
import 'visit_form_screen.dart';
import 'visit_model.dart';
import 'visit_service.dart';

class VisitListScreen extends StatefulWidget {
  const VisitListScreen({super.key});

  @override
  State<VisitListScreen> createState() => _VisitListScreenState();
}

class _VisitListScreenState extends State<VisitListScreen> {
  late final VisitService _service;
  DateTime _selectedDay = DateTime.now();
  DateTime _focusedDay = DateTime.now();
  CalendarFormat _calendarFormat = CalendarFormat.week;
  String? _typeFilter;

  Map<DateTime, List<Visit>> _monthVisits = {};
  bool _loading = true;
  String? _error;

  static const _typeFilters = [
    (null, 'Todas'),
    ('visit', 'Visitas'),
    ('meeting', 'Reuniones'),
    ('call', 'Llamadas'),
    ('signing', 'Firmas'),
  ];

  DateTime _dayKey(DateTime d) => DateTime(d.year, d.month, d.day);

  List<Visit> get _visitsOfSelectedDay {
    final all = _monthVisits[_dayKey(_selectedDay)] ?? const [];
    return _typeFilter == null
        ? all
        : all.where((v) => v.appointmentType == _typeFilter).toList();
  }

  @override
  void initState() {
    super.initState();
    _service = VisitService(context.read<AuthService>().odoo);
    _loadMonth(_focusedDay);
  }

  Future<void> _loadMonth(DateTime month) async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      // Rango con un colchón de una semana a cada lado para que las
      // celdas del mes anterior/siguiente visibles en la cuadrícula
      // también muestren su marcador de puntos.
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
      // Programa en el teléfono el aviso de las citas futuras que se acaban
      // de cargar, para que suene aunque la app esté cerrada.
      unawaited(VisitService.scheduleNotifications(visits));
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _openCreate,
        icon: const Icon(Icons.add),
        label: const Text('Cita'),
      ),
      body: Column(
        children: [
          Card(
            margin: const EdgeInsets.fromLTRB(12, 10, 12, 0),
            child: TableCalendar<Visit>(
              locale: 'es_EC',
              firstDay: DateTime.now().subtract(const Duration(days: 365)),
              lastDay: DateTime.now().add(const Duration(days: 365)),
              focusedDay: _focusedDay,
              currentDay: DateTime.now(),
              selectedDayPredicate: (day) => isSameDay(_selectedDay, day),
              calendarFormat: _calendarFormat,
              availableCalendarFormats: const {
                CalendarFormat.month: 'Mes',
                CalendarFormat.week: 'Semana',
              },
              eventLoader: (day) => _monthVisits[_dayKey(day)] ?? const [],
              onDaySelected: (selected, focused) {
                setState(() {
                  _selectedDay = selected;
                  _focusedDay = focused;
                });
              },
              onFormatChanged: (format) =>
                  setState(() => _calendarFormat = format),
              onPageChanged: (focused) {
                _focusedDay = focused;
                _loadMonth(focused);
              },
              headerStyle: const HeaderStyle(
                formatButtonShowsNext: false,
                titleCentered: true,
                formatButtonDecoration: BoxDecoration(
                  color: AppColors.neutralBg,
                  borderRadius: BorderRadius.all(Radius.circular(20)),
                ),
                formatButtonTextStyle: TextStyle(
                  fontSize: 12.5,
                  color: AppColors.navy,
                  fontWeight: FontWeight.w600,
                ),
                titleTextStyle: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  color: AppColors.ink,
                ),
                leftChevronIcon: Icon(
                  Icons.chevron_left,
                  color: AppColors.navy,
                ),
                rightChevronIcon: Icon(
                  Icons.chevron_right,
                  color: AppColors.navy,
                ),
              ),
              daysOfWeekStyle: const DaysOfWeekStyle(
                weekdayStyle: TextStyle(
                  fontSize: 11.5,
                  color: AppColors.mutedLight,
                  fontWeight: FontWeight.w600,
                ),
                weekendStyle: TextStyle(
                  fontSize: 11.5,
                  color: AppColors.mutedLight,
                  fontWeight: FontWeight.w600,
                ),
              ),
              calendarStyle: CalendarStyle(
                outsideDaysVisible: false,
                todayDecoration: BoxDecoration(
                  color: AppColors.accent.withValues(alpha: 0.15),
                  shape: BoxShape.circle,
                ),
                todayTextStyle: const TextStyle(
                  color: AppColors.accent,
                  fontWeight: FontWeight.w700,
                ),
                selectedDecoration: const BoxDecoration(
                  color: AppColors.navy,
                  shape: BoxShape.circle,
                ),
                selectedTextStyle: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w700,
                ),
                markerDecoration: const BoxDecoration(
                  color: AppColors.accent,
                  shape: BoxShape.circle,
                ),
                markersMaxCount: 3,
                markerSize: 5,
                markerMargin: const EdgeInsets.only(top: 3),
              ),
            ),
          ),
          const SizedBox(height: 6),
          ChoiceChipRow(
            options: _typeFilters,
            value: _typeFilter,
            onChanged: (v) => setState(() => _typeFilter = v),
          ),
          const SizedBox(height: 4),
          const Divider(height: 1),
          Expanded(
            child: RefreshIndicator(
              onRefresh: () => _loadMonth(_focusedDay),
              child: _buildBody(),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBody() {
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
        children: const [
          SizedBox(height: 60),
          MessageView(
            icon: Icons.event_available_outlined,
            message: 'No hay citas este día.',
          ),
        ],
      );
    }
    final timeFmt = DateFormat.Hm('es_EC');
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: visits.length,
      separatorBuilder: (_, _) => const SizedBox(height: 10),
      itemBuilder: (context, i) {
        final v = visits[i];
        return Card(
          child: InkWell(
            borderRadius: BorderRadius.circular(14),
            onTap: () => Navigator.of(context)
                .push(
                  MaterialPageRoute(
                    builder: (_) => VisitDetailScreen(visitId: v.id),
                  ),
                )
                .then((_) => _loadMonth(_focusedDay)),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 54,
                    padding: const EdgeInsets.symmetric(vertical: 6),
                    decoration: BoxDecoration(
                      color: AppColors.navy.withValues(alpha: 0.06),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    alignment: Alignment.center,
                    child: Text(
                      timeFmt.format(v.start),
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        color: AppColors.navy,
                        fontSize: 13,
                      ),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(
                              AppointmentTypeStyle.icon(v.appointmentType),
                              size: 15,
                              color: AppColors.muted,
                            ),
                            const SizedBox(width: 5),
                            Text(
                              AppointmentTypeStyle.label(v.appointmentType),
                              style: const TextStyle(
                                fontSize: 11.5,
                                color: AppColors.muted,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          v.propertyName.isNotEmpty ? v.propertyName : v.name,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            fontWeight: FontWeight.w700,
                            fontSize: 14.5,
                          ),
                        ),
                        if (v.clientName.isNotEmpty) ...[
                          const SizedBox(height: 2),
                          Text(
                            v.clientName,
                            style: const TextStyle(
                              fontSize: 12.5,
                              color: AppColors.muted,
                            ),
                          ),
                        ],
                        const SizedBox(height: 6),
                        AppBadge(
                          label: VisitStateStyle.label(v.visitState),
                          color: VisitStateStyle.color(v.visitState),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}
