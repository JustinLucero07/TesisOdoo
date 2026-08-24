import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
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
  int _sold = 0;
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
        odoo.callKw(
          model: 'estate.property',
          method: 'search_count',
          args: [
            [
              [
                'state',
                'in',
                ['sold', 'rented'],
              ],
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
          _sold = results[1] as int;
          _hotLeads = results[2] as int;
          _todayVisits = results[3] as List<Visit>;
          _activeContracts = results[4] as int;
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
          _DashboardHeader(userName: userName),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Barra de Accesos Rápidos
                _buildQuickActions(context),
                const SizedBox(height: 20),

                // Próxima Cita Destacada (si hay)
                if (_todayVisits.isNotEmpty) ...[
                  _buildNextVisitCard(_todayVisits.first, timeFmt, isDark),
                  const SizedBox(height: 20),
                ],

                // Indicadores Clave en formato Bento Grid
                const Text(
                  'Panel de Rendimiento',
                  style: TextStyle(
                    fontSize: 16.5,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.2,
                  ),
                ),
                const SizedBox(height: 12),
                _buildBentoGrid(isDark),

                const SizedBox(height: 24),
                // Sección de Visitas de Hoy
                ..._buildTodaySection(timeFmt, isDark),
              ],
            ),
          ),
        ],
      ),
    );
  }

  /// Barra de accesos directos rápidos
  Widget _buildQuickActions(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Acciones Rápidas',
          style: TextStyle(
            fontSize: 13.5,
            fontWeight: FontWeight.w700,
            color: AppColors.muted,
          ),
        ),
        const SizedBox(height: 10),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: [
              _ActionChipButton(
                icon: Icons.add_home_work_rounded,
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
              const SizedBox(width: 10),
              _ActionChipButton(
                icon: Icons.person_add_alt_1_rounded,
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
              const SizedBox(width: 10),
              _ActionChipButton(
                icon: Icons.calendar_month_rounded,
                label: 'Cita / Visita',
                isDark: isDark,
                onTap: () => Navigator.of(context)
                    .push(
                      MaterialPageRoute(
                        builder: (_) => const VisitFormScreen(),
                      ),
                    )
                    .then((_) => _load()),
              ),
              const SizedBox(width: 10),
              _ActionChipButton(
                icon: Icons.contact_phone_rounded,
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
            ],
          ),
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
        gradient: LinearGradient(
          colors: isInProgress
              ? [const Color(0xFF16A35A), const Color(0xFF0D6837)]
              : (isUpcomingSoon
                  ? [const Color(0xFF28235D), const Color(0xFF563D99)]
                  : [const Color(0xFF28235D), const Color(0xFF40398C)]),
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(22),
        boxShadow: [
          BoxShadow(
            color: (isInProgress ? const Color(0xFF16A35A) : const Color(0xFF28235D))
                .withValues(alpha: 0.28),
            blurRadius: 20,
            offset: const Offset(0, 8),
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
                  color: Colors.white.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (isInProgress) ...[
                      Container(
                        width: 7,
                        height: 7,
                        decoration: const BoxDecoration(
                          color: Colors.white,
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 5),
                      const Text(
                        'EN CURSO AHORA',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w900,
                          color: Colors.white,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ] else if (isUpcomingSoon) ...[
                      const Icon(Icons.bolt_rounded, size: 14, color: Colors.amberAccent),
                      const SizedBox(width: 3),
                      Text(
                        'EN $diffMinutes MIN',
                        style: const TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w900,
                          color: Colors.amberAccent,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ] else ...[
                      const Icon(Icons.access_time_rounded, size: 14, color: Colors.white),
                      const SizedBox(width: 5),
                      Text(
                        'Cita a las ${timeFmt.format(next.start)}',
                        style: const TextStyle(
                          fontSize: 12,
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
                    color: Colors.white.withValues(alpha: 0.18),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Row(
                    children: [
                      Text(
                        'Ver detalle',
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
              fontSize: 16.5,
              fontWeight: FontWeight.w800,
              color: Colors.white,
            ),
          ),
          if (next.clientName.isNotEmpty) ...[
            const SizedBox(height: 4),
            Row(
              children: [
                const Icon(Icons.person_rounded, size: 14, color: Colors.white70),
                const SizedBox(width: 4),
                Text(
                  next.clientName,
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                    color: Colors.white.withValues(alpha: 0.9),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  /// Bento Grid Modular de Métricas
  Widget _buildBentoGrid(bool isDark) {
    final totalInventory = _available + _sold;
    final availableRatio = totalInventory > 0 ? (_available / totalInventory) : 0.0;

    return Column(
      children: [
        // Tarjeta Bento Principal: Portafolio Inmobiliario (Ancho completo)
        InkWell(
          borderRadius: BorderRadius.circular(20),
          onTap: () => widget.onNavigate?.call(1),
          child: Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF1E1A3E) : Colors.white,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                color: isDark ? Colors.white12 : AppColors.line,
              ),
              boxShadow: softShadow(opacity: isDark ? 0.25 : 0.05, isDark: isDark),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: AppColors.info.withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: const Icon(
                            Icons.home_work_rounded,
                            size: 20,
                            color: AppColors.info,
                          ),
                        ),
                        const SizedBox(width: 10),
                        const Text(
                          'Portafolio Inmobiliario',
                          style: TextStyle(
                            fontSize: 14.5,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ],
                    ),
                    const Icon(Icons.arrow_forward_ios_rounded, size: 14, color: AppColors.mutedLight),
                  ],
                ),
                const SizedBox(height: 16),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '$_available',
                          style: TextStyle(
                            fontSize: 26,
                            fontWeight: FontWeight.w800,
                            color: isDark ? AppColors.navyLight : AppColors.navy,
                            letterSpacing: -0.5,
                          ),
                        ),
                        const Text(
                          'Disponibles',
                          style: TextStyle(fontSize: 12, color: AppColors.muted),
                        ),
                      ],
                    ),
                    Container(height: 30, width: 1, color: isDark ? Colors.white12 : AppColors.line),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '$_sold',
                          style: const TextStyle(
                            fontSize: 26,
                            fontWeight: FontWeight.w800,
                            color: AppColors.success,
                            letterSpacing: -0.5,
                          ),
                        ),
                        const Text(
                          'Vendidas/Arrendadas',
                          style: TextStyle(fontSize: 12, color: AppColors.muted),
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(
                    value: availableRatio,
                    minHeight: 6,
                    backgroundColor: AppColors.success.withValues(alpha: 0.2),
                    valueColor: AlwaysStoppedAnimation<Color>(
                      isDark ? AppColors.navyLight : AppColors.navy,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),

        // Fila de Tarjetas Bento Menores
        Row(
          children: [
            // Leads Calientes
            Expanded(
              child: _BentoMiniCard(
                icon: Icons.local_fire_department_rounded,
                iconColor: const Color(0xFFD81F26),
                title: 'Leads Calientes',
                value: '$_hotLeads',
                subtitle: 'Alta prioridad',
                isDark: isDark,
                onTap: () => widget.onNavigate?.call(2),
              ),
            ),
            const SizedBox(width: 12),
            // Visitas de Hoy
            Expanded(
              child: _BentoMiniCard(
                icon: Icons.calendar_month_rounded,
                iconColor: AppColors.navyLight,
                title: 'Visitas Hoy',
                value: '${_todayVisits.length}',
                subtitle: 'Programadas',
                isDark: isDark,
                onTap: () => widget.onNavigate?.call(3),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),

        // Contratos Activos
        _BentoMiniCard(
          icon: Icons.assignment_turned_in_rounded,
          iconColor: const Color(0xFF8B5CF6),
          title: 'Contratos Activos',
          value: '$_activeContracts',
          subtitle: 'Operaciones cerradas en curso',
          isDark: isDark,
          isWide: true,
          onTap: () => Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => const ContractListScreen()),
          ),
        ),
      ],
    );
  }

  List<Widget> _buildTodaySection(DateFormat timeFmt, bool isDark) {
    return [
      Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          const Text(
            'Agenda de Hoy',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
          ),
          TextButton(
            onPressed: () => widget.onNavigate?.call(3),
            child: const Text('Ver calendario completo'),
          ),
        ],
      ),
      const SizedBox(height: 6),
      if (_todayVisits.isEmpty)
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: isDark ? const Color(0xFF1E1A3E) : Colors.white,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: isDark ? Colors.white12 : AppColors.line),
          ),
          child: const Row(
            children: [
              Icon(Icons.check_circle_outline_rounded, color: AppColors.success),
              SizedBox(width: 12),
              Text(
                'No tienes visitas pendientes hoy.',
                style: TextStyle(color: AppColors.muted, fontSize: 13),
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
                  color: isDark ? Colors.white12 : AppColors.line,
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
                    color: AppColors.navy.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  alignment: Alignment.center,
                  child: Text(
                    timeFmt.format(v.start),
                    style: const TextStyle(
                      fontWeight: FontWeight.w800,
                      color: AppColors.navy,
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
                        style: const TextStyle(
                          fontSize: 12,
                          color: AppColors.muted,
                        ),
                      )
                    : null,
                trailing: const Icon(
                  Icons.arrow_forward_ios_rounded,
                  size: 14,
                  color: AppColors.mutedLight,
                ),
              ),
            ),
          ),
        ),
      ),
    ];
  }
}

class _BentoMiniCard extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final String title;
  final String value;
  final String subtitle;
  final bool isDark;
  final bool isWide;
  final VoidCallback onTap;

  const _BentoMiniCard({
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.value,
    required this.subtitle,
    required this.isDark,
    this.isWide = false,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(20),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF1E1A3E) : Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isDark ? Colors.white12 : AppColors.line,
          ),
          boxShadow: softShadow(opacity: isDark ? 0.25 : 0.05, isDark: isDark),
        ),
        child: isWide
            ? Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: iconColor.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(icon, size: 22, color: iconColor),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          title,
                          style: TextStyle(
                            fontSize: 13.5,
                            fontWeight: FontWeight.w600,
                            color: isDark ? Colors.white70 : AppColors.muted,
                          ),
                        ),
                        Text(
                          subtitle,
                          style: TextStyle(
                            fontSize: 11.5,
                            color: isDark ? Colors.white38 : AppColors.mutedLight,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Text(
                    value,
                    style: TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.w800,
                      color: isDark ? Colors.white : AppColors.ink,
                      letterSpacing: -0.5,
                    ),
                  ),
                  const SizedBox(width: 6),
                  const Icon(Icons.arrow_forward_ios_rounded, size: 14, color: AppColors.mutedLight),
                ],
              )
            : Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: iconColor.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Icon(icon, size: 18, color: iconColor),
                      ),
                      CustomPaint(
                        size: const Size(48, 22),
                        painter: _SparklinePainter(
                          color: iconColor,
                          data: const [12, 19, 15, 24, 22, 30, 28],
                          isDark: isDark,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Text(
                    value,
                    style: TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.w800,
                      color: isDark ? Colors.white : AppColors.ink,
                      letterSpacing: -0.5,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      color: isDark ? Colors.white : AppColors.ink,
                    ),
                  ),
                  Text(
                    subtitle,
                    style: TextStyle(
                      fontSize: 11,
                      color: isDark ? Colors.white38 : AppColors.mutedLight,
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}

/// Pintor personalizado para dibujar curvas de tendencia suaves (Sparklines) con gradiente
class _SparklinePainter extends CustomPainter {
  final Color color;
  final List<double> data;
  final bool isDark;

  const _SparklinePainter({
    required this.color,
    required this.data,
    required this.isDark,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (data.length < 2) return;
    final path = Path();
    final fillPath = Path();

    final maxVal = data.reduce((a, b) => a > b ? a : b);
    final minVal = data.reduce((a, b) => a < b ? a : b);
    final range = (maxVal - minVal) == 0 ? 1.0 : (maxVal - minVal);
    final stepX = size.width / (data.length - 1);

    for (int i = 0; i < data.length; i++) {
      final x = i * stepX;
      final normalized = (data[i] - minVal) / range;
      final y = size.height - (normalized * (size.height * 0.7) + size.height * 0.15);
      if (i == 0) {
        path.moveTo(x, y);
        fillPath.moveTo(x, size.height);
        fillPath.lineTo(x, y);
      } else {
        final prevX = (i - 1) * stepX;
        final prevNorm = (data[i - 1] - minVal) / range;
        final prevY = size.height - (prevNorm * (size.height * 0.7) + size.height * 0.15);
        final midX = (prevX + x) / 2;
        path.cubicTo(midX, prevY, midX, y, x, y);
        fillPath.cubicTo(midX, prevY, midX, y, x, y);
      }
    }

    fillPath.lineTo(size.width, size.height);
    fillPath.close();

    final fillPaint = Paint()
      ..shader = LinearGradient(
        colors: [
          color.withValues(alpha: isDark ? 0.35 : 0.2),
          color.withValues(alpha: 0.0),
        ],
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height))
      ..style = PaintingStyle.fill;

    final strokePaint = Paint()
      ..color = color.withValues(alpha: 0.9)
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    canvas.drawPath(fillPath, fillPaint);
    canvas.drawPath(path, strokePaint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _ActionChipButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool isDark;
  final VoidCallback onTap;

  const _ActionChipButton({
    required this.icon,
    required this.label,
    required this.isDark,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(14),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF262246) : AppColors.neutralBg,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: isDark ? Colors.white12 : AppColors.line.withValues(alpha: 0.7),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 17,
              color: isDark ? AppColors.navyLight : AppColors.navy,
            ),
            const SizedBox(width: 7),
            Text(
              label,
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w700,
                color: isDark ? Colors.white : AppColors.navy,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Encabezado moderno con degradado de marca y perfil del asesor
class _DashboardHeader extends StatelessWidget {
  final String userName;
  const _DashboardHeader({required this.userName});

  @override
  Widget build(BuildContext context) {
    final firstName = userName.trim().isNotEmpty ? userName.split(' ').first : 'Asesor';

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 24),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFF28235D),
            Color(0xFF18143C),
          ],
        ),
        borderRadius: BorderRadius.vertical(bottom: Radius.circular(28)),
      ),
      child: SafeArea(
        bottom: false,
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(3),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: const Color(0xFFD81F26),
                  width: 2,
                ),
              ),
              child: CircleAvatar(
                radius: 22,
                backgroundColor: Colors.white.withValues(alpha: 0.15),
                child: Text(
                  firstName.isNotEmpty ? firstName[0].toUpperCase() : 'A',
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w900,
                    fontSize: 18,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '¡Hola, $firstName! 👋',
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w800,
                      color: Colors.white,
                      letterSpacing: -0.3,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    DateFormat("EEEE d 'de' MMMM", 'es_EC').format(DateTime.now()),
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.8),
                      fontSize: 12.5,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(100),
                border: Border.all(
                  color: Colors.white.withValues(alpha: 0.18),
                ),
              ),
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.verified_rounded,
                    size: 14,
                    color: Color(0xFF10B981),
                  ),
                  SizedBox(width: 5),
                  Text(
                    'Inmobi Oficial',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      color: Colors.white,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
