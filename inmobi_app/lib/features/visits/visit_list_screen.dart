import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

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
  String? _typeFilter;
  List<Visit> _visits = [];
  bool _loading = true;
  String? _error;

  static const _typeFilters = [
    (null, 'Todas'),
    ('visit', 'Visitas'),
    ('meeting', 'Reuniones'),
    ('call', 'Llamadas'),
    ('signing', 'Firmas'),
  ];

  List<Visit> get _filteredVisits => _typeFilter == null
      ? _visits
      : _visits.where((v) => v.appointmentType == _typeFilter).toList();

  @override
  void initState() {
    super.initState();
    _service = VisitService(context.read<AuthService>().odoo);
    _load();
  }

  DateTime get _dayStart =>
      DateTime(_selectedDay.year, _selectedDay.month, _selectedDay.day);

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final result = await _service.listByRange(
        _dayStart,
        _dayStart.add(const Duration(days: 1)),
      );
      setState(() => _visits = result);
    } catch (e) {
      setState(() => _error = 'No se pudo cargar la agenda.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _selectDay(DateTime day) {
    setState(() => _selectedDay = day);
    _load();
  }

  Future<void> _openCreate() async {
    final saved = await Navigator.of(
      context,
    ).push<bool>(MaterialPageRoute(builder: (_) => const VisitFormScreen()));
    if (saved == true) _load();
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
          _DateStrip(selected: _selectedDay, onSelect: _selectDay),
          const Divider(height: 1),
          const SizedBox(height: 8),
          ChoiceChipRow(
            options: _typeFilters,
            value: _typeFilter,
            onChanged: (v) => setState(() => _typeFilter = v),
          ),
          const SizedBox(height: 4),
          Expanded(
            child: RefreshIndicator(onRefresh: _load, child: _buildBody()),
          ),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_loading) return const SkeletonList();
    if (_error != null) {
      return MessageView(
        icon: Icons.error_outline,
        message: _error!,
        onRetry: _load,
      );
    }
    final visits = _filteredVisits;
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
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => VisitDetailScreen(visitId: v.id),
              ),
            ),
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

/// Franja horizontal de 14 días (hoy ± 1 semana) para elegir el día de la
/// agenda, sin agregar una dependencia externa de calendario.
class _DateStrip extends StatelessWidget {
  final DateTime selected;
  final ValueChanged<DateTime> onSelect;
  const _DateStrip({required this.selected, required this.onSelect});

  @override
  Widget build(BuildContext context) {
    final today = DateTime.now();
    final days = List.generate(
      14,
      (i) => DateTime(
        today.year,
        today.month,
        today.day,
      ).add(Duration(days: i - 3)),
    );
    final dayFmt = DateFormat.E('es_EC');

    return SizedBox(
      height: 78,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        itemCount: days.length,
        separatorBuilder: (_, _) => const SizedBox(width: 8),
        itemBuilder: (context, i) {
          final d = days[i];
          final isSelected =
              d.year == selected.year &&
              d.month == selected.month &&
              d.day == selected.day;
          final isToday =
              d.year == today.year &&
              d.month == today.month &&
              d.day == today.day;
          return InkWell(
            onTap: () => onSelect(d),
            borderRadius: BorderRadius.circular(12),
            child: Container(
              width: 52,
              decoration: BoxDecoration(
                color: isSelected ? AppColors.navy : Colors.white,
                border: Border.all(
                  color: isSelected ? AppColors.navy : AppColors.line,
                ),
                borderRadius: BorderRadius.circular(12),
              ),
              alignment: Alignment.center,
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    dayFmt.format(d).replaceAll('.', ''),
                    style: TextStyle(
                      fontSize: 11,
                      color: isSelected ? Colors.white70 : AppColors.muted,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${d.day}',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: isSelected
                          ? Colors.white
                          : (isToday ? AppColors.accent : AppColors.ink),
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
