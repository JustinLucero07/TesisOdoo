import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/odoo_image.dart';
import '../../core/widgets/states.dart';
import '../auth/auth_service.dart';
import '../contacts/contact_form_screen.dart';
import '../contracts/contract_list_screen.dart';
import '../crm/lead_form_screen.dart';
import '../crm/lead_service.dart';
import '../properties/property_form_screen.dart';
import '../visits/visit_detail_screen.dart';
import '../visits/visit_form_screen.dart';
import '../visits/visit_model.dart';
import '../visits/visit_service.dart';

class DashboardScreen extends StatefulWidget {
  final ValueChanged<int>? onNavigate;
  const DashboardScreen({super.key, this.onNavigate});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  bool _loading = true;
  String? _error;
  int _available = 0;
  int _hotLeads = 0;
  int _activeContracts = 0;
  List<Visit> _todayVisits = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final odoo = context.read<AuthService>().odoo;
      final leadService = LeadService(odoo);
      final visitService = VisitService(odoo);
      final now = DateTime.now();
      final dayStart = DateTime(now.year, now.month, now.day);

      final results = await Future.wait([
        odoo.callKw(
          model: 'estate.property',
          method: 'search_count',
          args: [
            [
              ['state', '=', 'available'],
            ],
          ],
        ),
        leadService.countHot(),
        visitService.listByRange(
          dayStart,
          dayStart.add(const Duration(days: 1)),
        ),
        odoo.callKw(
          model: 'estate.contract',
          method: 'search_count',
          args: [
            [
              ['state', '=', 'active'],
            ],
          ],
        ),
      ]);

      if (mounted) {
        setState(() {
          _available = results[0] as int;
          _hotLeads = results[1] as int;
          _todayVisits = results[2] as List<Visit>;
          _activeContracts = results[3] as int;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _error = 'No se pudieron cargar los indicadores.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final userName = context.watch<AuthService>().userName ?? '';
    final isDark = Theme.of(context).brightness == Brightness.dark;

    if (_loading) return const LoadingView();
    if (_error != null) {
      return MessageView(
        icon: Icons.error_outline,
        message: _error!,
        onRetry: _load,
      );
    }

    final timeFmt = DateFormat.Hm('es_EC');

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.only(bottom: 110),
        children: [
          // ── Encabezado Ejecutivo con Saludo Dinámico ──
          _DashboardHeader(userName: userName),

          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // ── Accesos Rápidos Inmediatos ──
                _buildQuickActions(context, isDark),
                const SizedBox(height: 18),

                // ── Próxima Cita / Actividad en Vivo ──
                if (_todayVisits.isNotEmpty) ...[
                  _buildNextVisitCard(_todayVisits.first, timeFmt, isDark),
                  const SizedBox(height: 20),
                ] else ...[
                  _buildEmptyAgendaCard(isDark),
                  const SizedBox(height: 20),
                ],

                // ── Panel de Rendimiento (Bento Grid) ──
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Rendimiento Operativo',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                        color: isDark ? Colors.white : const Color(0xFF0F172A),
                        letterSpacing: -0.2,
                      ),
                    ),
                    Text(
                      'En tiempo real',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                _buildBentoGrid(isDark),

                const SizedBox(height: 24),
                // ── Sección de Agenda del Día ──
                ..._buildTodaySection(timeFmt, isDark),
              ],
            ),
          ),
        ],
      ),
    );
  }

  /// Barra de accesos directos rápidos
  Widget _buildQuickActions(BuildContext context, bool isDark) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'ACCIONES RÁPIDAS',
          style: TextStyle(
            fontSize: 11.5,
            fontWeight: FontWeight.w800,
            letterSpacing: 0.8,
            color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
          ),
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(
              child: _ActionSquareButton(
                icon: Icons.add_home_work_rounded,
                iconColor: const Color(0xFF2563EB),
                bgColor: isDark
                    ? const Color(0xFF1E3A8A).withValues(alpha: 0.35)
                    : const Color(0xFFEFF6FF),
                label: 'Propiedad',
                isDark: isDark,
                onTap: () => Navigator.of(context)
                    .push(
                      MaterialPageRoute(
                        builder: (_) => const PropertyFormScreen(),
                      ),
                    )
                    .then((_) => _load()),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _ActionSquareButton(
                icon: Icons.person_add_alt_1_rounded,
                iconColor: const Color(0xFFDC2626),
                bgColor: isDark
                    ? const Color(0xFF7F1D1D).withValues(alpha: 0.35)
                    : const Color(0xFFFEF2F2),
                label: 'Lead',
                isDark: isDark,
                onTap: () => Navigator.of(context)
                    .push(
                      MaterialPageRoute(
                        builder: (_) => const LeadFormScreen(),
                      ),
                    )
                    .then((_) => _load()),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _ActionSquareButton(
                icon: Icons.calendar_month_rounded,
                iconColor: const Color(0xFFD97706),
                bgColor: isDark
                    ? const Color(0xFF78350F).withValues(alpha: 0.35)
                    : const Color(0xFFFEF3C7),
                label: 'Cita',
                isDark: isDark,
                onTap: () => Navigator.of(context)
                    .push(
                      MaterialPageRoute(
                        builder: (_) => const VisitFormScreen(),
                      ),
                    )
                    .then((_) => _load()),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _ActionSquareButton(
                icon: Icons.contact_phone_rounded,
                iconColor: const Color(0xFF059669),
                bgColor: isDark
                    ? const Color(0xFF064E3B).withValues(alpha: 0.35)
                    : const Color(0xFFECFDF5),
                label: 'Contacto',
                isDark: isDark,
                onTap: () => Navigator.of(context)
                    .push(
                      MaterialPageRoute(
                        builder: (_) => const ContactFormScreen(),
                      ),
                    )
                    .then((_) => _load()),
              ),
            ),
          ],
        ),
      ],
    );
  }

  /// Tarjeta destacada de la próxima cita del día con indicador de actividad en vivo
  Widget _buildNextVisitCard(Visit next, DateFormat timeFmt, bool isDark) {
    final now = DateTime.now();
    final diffMinutes = next.start.difference(now).inMinutes;
    final isUpcomingSoon = diffMinutes >= 0 && diffMinutes <= 45;
    final isInProgress = now.isAfter(next.start) && (next.stop == null || now.isBefore(next.stop!));

    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFF28235D),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: isInProgress ? const Color(0xFF10B981) : Colors.white12,
          width: isInProgress ? 1.5 : 1,
        ),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF28235D).withValues(alpha: 0.25),
            blurRadius: 16,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: isInProgress
                      ? const Color(0xFF10B981)
                      : Colors.white.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(100),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (isInProgress) ...[
                      const Icon(Icons.radio_button_checked_rounded, size: 12, color: Colors.white),
                      const SizedBox(width: 5),
                      const Text(
                        'EN CURSO AHORA',
                        style: TextStyle(
                          fontSize: 10.5,
                          fontWeight: FontWeight.w800,
                          color: Colors.white,
                          letterSpacing: 0.4,
                        ),
                      ),
                    ] else if (isUpcomingSoon) ...[
                      const Icon(Icons.bolt_rounded, size: 14, color: Colors.amberAccent),
                      const SizedBox(width: 3),
                      Text(
                        'EN $diffMinutes MIN',
                        style: const TextStyle(
                          fontSize: 10.5,
                          fontWeight: FontWeight.w800,
                          color: Colors.amberAccent,
                          letterSpacing: 0.4,
                        ),
                      ),
                    ] else ...[
                      const Icon(Icons.access_time_rounded, size: 13, color: Colors.white70),
                      const SizedBox(width: 4),
                      Text(
                        'Hoy · ${timeFmt.format(next.start)}',
                        style: const TextStyle(
                          fontSize: 11.5,
                          fontWeight: FontWeight.w700,
                          color: Colors.white,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              const Spacer(),
              InkWell(
                borderRadius: BorderRadius.circular(10),
                onTap: () => Navigator.of(context)
                    .push(
                      MaterialPageRoute(
                        builder: (_) => VisitDetailScreen(visitId: next.id),
                      ),
                    )
                    .then((_) => _load()),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Row(
                    children: [
                      Text(
                        'Ver cita',
                        style: TextStyle(
                          fontSize: 11.5,
                          fontWeight: FontWeight.w700,
                          color: Colors.white,
                        ),
                      ),
                      SizedBox(width: 4),
                      Icon(Icons.arrow_forward_ios_rounded, size: 10, color: Colors.white),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            next.propertyName.isNotEmpty ? next.propertyName : next.name,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w800,
              color: Colors.white,
            ),
          ),
          if (next.clientName.isNotEmpty) ...[
            const SizedBox(height: 4),
            Row(
              children: [
                const Icon(Icons.person_rounded, size: 14, color: Colors.white70),
                const SizedBox(width: 5),
                Text(
                  next.clientName,
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                    color: Colors.white.withValues(alpha: 0.85),
                  ),
                ),
              ],
            ),
          ],
          const SizedBox(height: 14),

          // Botones de acción directa en la tarjeta de cita
          Row(
            children: [
              _GlassActionButton(
                icon: Icons.chat_bubble_rounded,
                label: 'WhatsApp',
                color: const Color(0xFF25D366),
                onTap: () => _openWhatsAppVisit(next),
              ),
              if (next.location.isNotEmpty || next.propertyName.isNotEmpty) ...[
                const SizedBox(width: 8),
                _GlassActionButton(
                  icon: Icons.location_on_rounded,
                  label: 'Ubicación',
                  color: Colors.white,
                  onTap: () => _openLocationVisit(next),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }

  /// Tarjeta cuando no hay citas hoy
  Widget _buildEmptyAgendaCard(bool isDark) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1E1A3E) : Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: isDark ? Colors.white12 : const Color(0xFFE2E8F0),
        ),
        boxShadow: softShadow(opacity: isDark ? 0.2 : 0.035, isDark: isDark),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: const Color(0xFF10B981).withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(
              Icons.event_available_rounded,
              color: Color(0xFF10B981),
              size: 22,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Agenda al día',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: isDark ? Colors.white : const Color(0xFF0F172A),
                  ),
                ),
                Text(
                  'No tienes citas programadas para hoy',
                  style: TextStyle(
                    fontSize: 12,
                    color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                  ),
                ),
              ],
            ),
          ),
          TextButton(
            onPressed: () => Navigator.of(context)
                .push(
                  MaterialPageRoute(builder: (_) => const VisitFormScreen()),
                )
                .then((_) => _load()),
            child: const Text('+ Agendar'),
          ),
        ],
      ),
    );
  }

  /// Bento Grid de Rendimiento
  Widget _buildBentoGrid(bool isDark) {
    return Column(
      children: [
        Row(
          children: [
            // Propiedades Disponibles
            Expanded(
              child: _MetricCard(
                icon: Icons.home_work_rounded,
                iconColor: const Color(0xFF2563EB),
                value: '$_available',
                title: 'Propiedades',
                subtitle: 'En catálogo',
                isDark: isDark,
                onTap: () => widget.onNavigate?.call(1),
              ),
            ),
            const SizedBox(width: 10),
            // Leads Calientes
            Expanded(
              child: _MetricCard(
                icon: Icons.local_fire_department_rounded,
                iconColor: const Color(0xFFDC2626),
                value: '$_hotLeads',
                title: 'Leads Hot',
                subtitle: 'Alta prioridad',
                isDark: isDark,
                onTap: () => widget.onNavigate?.call(2),
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            // Visitas de Hoy
            Expanded(
              child: _MetricCard(
                icon: Icons.calendar_month_rounded,
                iconColor: const Color(0xFFD97706),
                value: '${_todayVisits.length}',
                title: 'Citas Hoy',
                subtitle: 'Programadas',
                isDark: isDark,
                onTap: () => widget.onNavigate?.call(3),
              ),
            ),
            const SizedBox(width: 10),
            // Contratos
            Expanded(
              child: _MetricCard(
                icon: Icons.assignment_turned_in_rounded,
                iconColor: const Color(0xFF059669),
                value: '$_activeContracts',
                title: 'Contratos',
                subtitle: 'En gestión',
                isDark: isDark,
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const ContractListScreen()),
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  List<Widget> _buildTodaySection(DateFormat timeFmt, bool isDark) {
    return [
      Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            'Agenda de Hoy',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w800,
              color: isDark ? Colors.white : const Color(0xFF0F172A),
            ),
          ),
          TextButton(
            onPressed: () => widget.onNavigate?.call(3),
            child: const Text('Ver calendario'),
          ),
        ],
      ),
      const SizedBox(height: 6),
      if (_todayVisits.isEmpty)
        Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            color: isDark ? const Color(0xFF1E1A3E) : Colors.white,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: isDark ? Colors.white12 : const Color(0xFFE2E8F0),
            ),
          ),
          child: Row(
            children: [
              const Icon(Icons.check_circle_outline_rounded, color: Color(0xFF10B981)),
              const SizedBox(width: 12),
              Text(
                'No tienes más visitas pendientes hoy.',
                style: TextStyle(
                  color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                  fontSize: 13,
                ),
              ),
            ],
          ),
        )
      else
        ..._todayVisits.map(
          (v) => Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Container(
              decoration: BoxDecoration(
                color: isDark ? const Color(0xFF1E1A3E) : Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: isDark ? Colors.white12 : const Color(0xFFE2E8F0),
                ),
                boxShadow: softShadow(
                  opacity: isDark ? 0.2 : 0.03,
                  isDark: isDark,
                ),
              ),
              child: Material(
                color: Colors.transparent,
                child: ListTile(
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),
                  onTap: () => Navigator.of(context)
                      .push(
                        MaterialPageRoute(
                          builder: (_) => VisitDetailScreen(visitId: v.id),
                        ),
                      )
                      .then((_) => _load()),
                  leading: Container(
                    width: 48,
                    padding: const EdgeInsets.symmetric(vertical: 6),
                    decoration: BoxDecoration(
                      color: const Color(0xFF28235D).withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    alignment: Alignment.center,
                    child: Text(
                      timeFmt.format(v.start),
                      style: const TextStyle(
                        fontWeight: FontWeight.w800,
                        color: Color(0xFF28235D),
                        fontSize: 12,
                      ),
                    ),
                  ),
                  title: Text(
                    v.propertyName.isNotEmpty ? v.propertyName : v.name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 14,
                    ),
                  ),
                  subtitle: v.clientName.isNotEmpty
                      ? Text(
                          v.clientName,
                          style: TextStyle(
                            fontSize: 12,
                            color: isDark
                                ? const Color(0xFF94A3B8)
                                : const Color(0xFF64748B),
                          ),
                        )
                      : null,
                  trailing: const Icon(
                    Icons.arrow_forward_ios_rounded,
                    size: 13,
                    color: Color(0xFF94A3B8),
                  ),
                ),
              ),
            ),
          ),
        ),
    ];
  }

  Future<void> _openWhatsAppVisit(Visit visit) async {
    HapticFeedback.selectionClick();
    String phone = '';
    if (visit.clientId != null) {
      try {
        final odoo = context.read<AuthService>().odoo;
        final res = await odoo.searchRead(
          model: 'res.partner',
          domain: [
            ['id', '=', visit.clientId],
          ],
          fields: ['phone', 'mobile'],
          limit: 1,
        );
        if (res.isNotEmpty) {
          final m = (res.first['mobile'] ?? '').toString().trim();
          final p = (res.first['phone'] ?? '').toString().trim();
          phone = m.isNotEmpty ? m : p;
        }
      } catch (_) {}
    }

    final clientName = visit.clientName.isNotEmpty ? visit.clientName : 'Estimado/a';
    final prop = visit.propertyName.isNotEmpty ? 'la propiedad ${visit.propertyName}' : 'nuestra cita inmobiliaria';
    final timeStr = DateFormat.Hm('es_EC').format(visit.start);
    final msg = Uri.encodeComponent(
      'Hola $clientName, te saludo de Inmobi Inmobiliaria respecto a $prop programada para las $timeStr.',
    );

    Uri uri;
    if (phone.isNotEmpty) {
      final digits = phone.replaceAll(RegExp(r'[^0-9]'), '');
      uri = Uri.parse('https://wa.me/$digits?text=$msg');
    } else {
      uri = Uri.parse('https://wa.me/?text=$msg');
    }

    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  Future<void> _openLocationVisit(Visit visit) async {
    HapticFeedback.selectionClick();
    final query = visit.location.isNotEmpty ? visit.location : visit.propertyName;
    if (query.isEmpty) return;

    final uri = Uri.parse(
      'https://www.google.com/maps/search/?api=1&query=${Uri.encodeComponent('$query Ecuador')}',
    );
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }
}

class _MetricCard extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final String value;
  final String title;
  final String subtitle;
  final bool isDark;
  final VoidCallback onTap;

  const _MetricCard({
    required this.icon,
    required this.iconColor,
    required this.value,
    required this.title,
    required this.subtitle,
    required this.isDark,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(18),
      onTap: () {
        HapticFeedback.lightImpact();
        onTap();
      },
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF1E1A3E) : Colors.white,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(
            color: isDark ? Colors.white12 : const Color(0xFFE2E8F0),
          ),
          boxShadow: softShadow(opacity: isDark ? 0.2 : 0.035, isDark: isDark),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: iconColor.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(icon, size: 18, color: iconColor),
                ),
                Icon(
                  Icons.arrow_forward_ios_rounded,
                  size: 11,
                  color: isDark ? const Color(0xFF64748B) : const Color(0xFFCBD5E1),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              value,
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w800,
                color: isDark ? Colors.white : const Color(0xFF0F172A),
                letterSpacing: -0.5,
              ),
            ),
            const SizedBox(height: 1),
            Text(
              title,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 12.5,
                fontWeight: FontWeight.w700,
                color: isDark ? Colors.white : const Color(0xFF0F172A),
              ),
            ),
            Text(
              subtitle,
              style: TextStyle(
                fontSize: 11,
                color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _GlassActionButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  const _GlassActionButton({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Material(
        color: Colors.white.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(10),
        child: InkWell(
          borderRadius: BorderRadius.circular(10),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(icon, size: 14, color: color),
                const SizedBox(width: 6),
                Text(
                  label,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _ActionSquareButton extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final Color bgColor;
  final String label;
  final bool isDark;
  final VoidCallback onTap;

  const _ActionSquareButton({
    required this.icon,
    required this.iconColor,
    required this.bgColor,
    required this.label,
    required this.isDark,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1E1A3E) : Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: isDark ? Colors.white12 : const Color(0xFFE2E8F0),
        ),
        boxShadow: softShadow(opacity: isDark ? 0.2 : 0.035, isDark: isDark),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: () {
            HapticFeedback.lightImpact();
            onTap();
          },
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 4),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 38,
                  height: 38,
                  decoration: BoxDecoration(
                    color: bgColor,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(icon, size: 20, color: iconColor),
                ),
                const SizedBox(height: 7),
                Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 11.5,
                    fontWeight: FontWeight.w700,
                    color: isDark ? Colors.white : const Color(0xFF0F172A),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Encabezado dinámico con saludo por hora y perfil del asesor
class _DashboardHeader extends StatelessWidget {
  final String userName;
  const _DashboardHeader({required this.userName});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthService>();
    final firstName = userName.trim().isNotEmpty ? userName.split(' ').first : 'Asesor';

    final hour = DateTime.now().hour;
    final greeting = hour < 12
        ? 'Buenos días'
        : (hour < 19 ? 'Buenas tardes' : 'Buenas noches');

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(20, 18, 20, 22),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFF28235D),
            Color(0xFF1E1A46),
          ],
        ),
        borderRadius: BorderRadius.vertical(bottom: Radius.circular(26)),
      ),
      child: SafeArea(
        bottom: false,
        child: Row(
          children: [
            // Avatar del usuario con borde suave
            Container(
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: Colors.white.withValues(alpha: 0.35),
                  width: 2,
                ),
              ),
              child: UserAvatar(
                odoo: auth.odoo,
                userId: auth.odoo.userId ?? 0,
                userName: firstName,
                radius: 22,
                backgroundColor: const Color(0xFF4338CA),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    greeting,
                    style: TextStyle(
                      fontSize: 12.5,
                      fontWeight: FontWeight.w600,
                      color: Colors.white.withValues(alpha: 0.75),
                      letterSpacing: 0.2,
                    ),
                  ),
                  const SizedBox(height: 1),
                  Text(
                    firstName,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 19,
                      fontWeight: FontWeight.w800,
                      color: Colors.white,
                      letterSpacing: -0.3,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Row(
                    children: [
                      Container(
                        width: 7,
                        height: 7,
                        decoration: const BoxDecoration(
                          color: Color(0xFF10B981),
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        'En línea · Odoo ERP',
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.8),
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                DateFormat("d MMM", 'es_EC').format(DateTime.now()).toUpperCase(),
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                  fontSize: 12,
                  letterSpacing: 0.5,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
