import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/kpi_card.dart';
import '../../core/widgets/states.dart';
import '../auth/auth_service.dart';
import '../contracts/contract_list_screen.dart';
import '../crm/lead_service.dart';
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

      setState(() {
        _available = results[0] as int;
        _sold = results[1] as int;
        _hotLeads = results[2] as int;
        _todayVisits = results[3] as List<Visit>;
        _activeContracts = results[4] as int;
      });
    } catch (e) {
      setState(() => _error = 'No se pudieron cargar los indicadores.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final userName = context.watch<AuthService>().userName ?? '';
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
        padding: EdgeInsets.zero,
        children: [
          _DashboardHeader(userName: userName),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 18, 16, 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [_buildKpiGrid(), ..._buildTodaySection(timeFmt)],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildKpiGrid() {
    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 12,
      crossAxisSpacing: 12,
      childAspectRatio: 1.35,
      children: [
        KpiCard(
          icon: Icons.home_work_outlined,
          value: '$_available',
          label: 'Disponibles',
          accent: AppColors.info,
          onTap: () => widget.onNavigate?.call(1),
        ),
        KpiCard(
          icon: Icons.local_fire_department,
          value: '$_hotLeads',
          label: 'Leads calientes',
          accent: AppColors.danger,
          onTap: () => widget.onNavigate?.call(2),
        ),
        KpiCard(
          icon: Icons.event_available_outlined,
          value: '${_todayVisits.length}',
          label: 'Visitas hoy',
          accent: AppColors.accent,
          onTap: () => widget.onNavigate?.call(3),
        ),
        KpiCard(
          icon: Icons.sell_outlined,
          value: '$_sold',
          label: 'Vendidas/arrendadas',
          accent: AppColors.success,
        ),
        KpiCard(
          icon: Icons.description_outlined,
          value: '$_activeContracts',
          label: 'Contratos activos',
          accent: AppColors.navyLight,
          onTap: () => Navigator.of(
            context,
          ).push(MaterialPageRoute(builder: (_) => const ContractListScreen())),
        ),
      ],
    );
  }

  List<Widget> _buildTodaySection(DateFormat timeFmt) {
    return [
      const SizedBox(height: 24),
      const Text(
        'Visitas de hoy',
        style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
      ),
      const SizedBox(height: 10),
      if (_todayVisits.isEmpty)
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Row(
              children: const [
                Icon(Icons.check_circle_outline, color: AppColors.success),
                SizedBox(width: 10),
                Text(
                  'No tienes visitas agendadas hoy.',
                  style: TextStyle(color: AppColors.muted, fontSize: 13),
                ),
              ],
            ),
          ),
        )
      else
        ..._todayVisits.map(
          (v) => Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Row(
                  children: [
                    Container(
                      width: 46,
                      padding: const EdgeInsets.symmetric(vertical: 6),
                      decoration: BoxDecoration(
                        color: AppColors.navy.withValues(alpha: 0.06),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      alignment: Alignment.center,
                      child: Text(
                        timeFmt.format(v.start),
                        style: const TextStyle(
                          fontWeight: FontWeight.w700,
                          color: AppColors.navy,
                          fontSize: 12.5,
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        v.propertyName.isNotEmpty ? v.propertyName : v.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontWeight: FontWeight.w600,
                          fontSize: 13.5,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
    ];
  }
}

/// Encabezado con degradado de marca — saludo + fecha, con un patrón sutil
/// de fondo para que el dashboard no arranque plano.
class _DashboardHeader extends StatelessWidget {
  final String userName;
  const _DashboardHeader({required this.userName});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [AppColors.navy, AppColors.navyDeep],
        ),
        borderRadius: BorderRadius.vertical(bottom: Radius.circular(28)),
      ),
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Positioned(
            right: -30,
            top: -30,
            child: Icon(
              Icons.home_work_outlined,
              size: 140,
              color: Colors.white.withValues(alpha: 0.06),
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Hola, ${userName.split(' ').first} 👋',
                style: const TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                DateFormat("EEEE d 'de' MMMM", 'es_EC').format(DateTime.now()),
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.75),
                  fontSize: 13,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
