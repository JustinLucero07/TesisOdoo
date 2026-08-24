import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/app_badge.dart';
import '../../core/widgets/states.dart';
import '../auth/auth_service.dart';
import 'crm_stage_service.dart';
import 'lead_detail_screen.dart';
import 'lead_form_screen.dart';
import 'lead_model.dart';
import 'lead_service.dart';

/// Embudo vertical: una columna por etapa del CRM (las reales de
/// `crm.stage`), que se recorren deslizando de lado. Dentro de cada
/// columna, las oportunidades se apilan verticalmente — el mismo kanban
/// del ERP, adaptado a una pantalla angosta.
class LeadFunnelScreen extends StatefulWidget {
  final bool isPostSale;
  const LeadFunnelScreen({super.key, this.isPostSale = false});

  @override
  State<LeadFunnelScreen> createState() => _LeadFunnelScreenState();
}

class _LeadFunnelScreenState extends State<LeadFunnelScreen> {
  late final LeadService _leadService;
  late final CrmStageService _stageService;
  final _pageController = PageController(viewportFraction: 0.88);

  List<CrmStage> _stages = [];
  Map<int, List<Lead>> _leadsByStage = {};
  bool _loading = true;
  String? _error;
  int _currentPage = 0;

  @override
  void initState() {
    super.initState();
    final odoo = context.read<AuthService>().odoo;
    _leadService = LeadService(odoo);
    _stageService = CrmStageService(odoo);
    _load();
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final stages = await _stageService.list(isPostSale: widget.isPostSale);
      // Una sola consulta para todas las etapas: se traen las oportunidades
      // y se agrupan en memoria, en vez de una consulta por columna.
      final leads = await _leadService.list(limit: 300);
      final grouped = <int, List<Lead>>{};
      for (final lead in leads) {
        if (lead.stageId == null) continue;
        grouped.putIfAbsent(lead.stageId!, () => []).add(lead);
      }
      if (mounted) {
        setState(() {
          _stages = stages;
          _leadsByStage = grouped;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _error = 'No se pudo cargar el embudo.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _openCreate() async {
    final saved = await Navigator.of(
      context,
    ).push<bool>(MaterialPageRoute(builder: (_) => const LeadFormScreen()));
    if (saved == true) _load();
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const LoadingView();
    if (_error != null) {
      return MessageView(
        icon: Icons.error_outline,
        message: _error!,
        onRetry: _load,
      );
    }
    if (_stages.isEmpty) {
      return const MessageView(
        icon: Icons.view_column_outlined,
        message: 'No hay etapas configuradas.',
      );
    }

    final currency = NumberFormat.currency(
      locale: 'es_EC',
      symbol: '\$',
      decimalDigits: 0,
    );

    return Scaffold(
      floatingActionButton: Padding(
        padding: const EdgeInsets.only(bottom: 74),
        child: FloatingActionButton.small(
          heroTag: null,
          onPressed: _openCreate,
          elevation: 4,
          backgroundColor: const Color(0xFFD81F26),
          tooltip: 'Nuevo Lead',
          child: const Icon(Icons.person_add_alt_1_rounded, color: Colors.white, size: 20),
        ),
      ),
      body: Column(
        children: [
          Expanded(
            child: PageView.builder(
              controller: _pageController,
              itemCount: _stages.length,
              onPageChanged: (i) => setState(() => _currentPage = i),
              itemBuilder: (context, i) {
                final stage = _stages[i];
                final leads = _leadsByStage[stage.id] ?? const <Lead>[];
                return _StageColumn(
                  stage: stage,
                  leads: leads,
                  currency: currency,
                  onRefresh: _load,
                );
              },
            ),
          ),
          // Indicador de posición dentro del embudo
          Padding(
            padding: const EdgeInsets.fromLTRB(0, 4, 0, 78),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(
                _stages.length,
                (i) => AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  margin: const EdgeInsets.symmetric(horizontal: 3),
                  width: i == _currentPage ? 18 : 6,
                  height: 6,
                  decoration: BoxDecoration(
                    color: i == _currentPage ? AppColors.navy : AppColors.line,
                    borderRadius: BorderRadius.circular(3),
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

class _StageColumn extends StatelessWidget {
  final CrmStage stage;
  final List<Lead> leads;
  final NumberFormat currency;
  final VoidCallback onRefresh;

  const _StageColumn({
    required this.stage,
    required this.leads,
    required this.currency,
    required this.onRefresh,
  });

  @override
  Widget build(BuildContext context) {
    final total = leads.fold<double>(0, (sum, l) => sum + l.clientBudget);
    final accent = stage.isLost ? AppColors.danger : AppColors.navy;

    return Container(
      margin: const EdgeInsets.fromLTRB(8, 10, 8, 0),
      decoration: BoxDecoration(
        color: AppColors.neutralBg,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        children: [
          // Cabecera de la columna, con la franja de color arriba
          Container(
            decoration: BoxDecoration(
              color: accent,
              borderRadius: const BorderRadius.vertical(
                top: Radius.circular(16),
              ),
            ),
            height: 4,
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 12, 14, 10),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        stage.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 15,
                        ),
                      ),
                      if (total > 0) ...[
                        const SizedBox(height: 2),
                        Text(
                          currency.format(total),
                          style: const TextStyle(
                            fontSize: 12,
                            color: AppColors.muted,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 9,
                    vertical: 3,
                  ),
                  decoration: BoxDecoration(
                    color: accent.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    '${leads.length}',
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 12.5,
                      color: accent,
                    ),
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: leads.isEmpty
                ? const Center(
                    child: Text(
                      'Sin oportunidades\nen esta etapa',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: AppColors.mutedLight,
                        fontSize: 12.5,
                      ),
                    ),
                  )
                : ListView.separated(
                    padding: const EdgeInsets.fromLTRB(10, 0, 10, 100),
                    itemCount: leads.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 8),
                    itemBuilder: (context, i) => _FunnelCard(
                      lead: leads[i],
                      currency: currency,
                      onRefresh: onRefresh,
                    ),
                  ),
          ),
        ],
      ),
    );
  }
}

class _FunnelCard extends StatelessWidget {
  final Lead lead;
  final NumberFormat currency;
  final VoidCallback onRefresh;

  const _FunnelCard({
    required this.lead,
    required this.currency,
    required this.onRefresh,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColors.surface,
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => Navigator.of(context)
            .push(
              MaterialPageRoute(
                builder: (_) => LeadDetailScreen(leadId: lead.id),
              ),
            )
            .then((_) => onRefresh()),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      lead.name,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 13.5,
                      ),
                    ),
                  ),
                  Icon(
                    LeadTemperatureStyle.icon(lead.leadTemperature),
                    size: 15,
                    color: LeadTemperatureStyle.color(lead.leadTemperature),
                  ),
                ],
              ),
              if (lead.contactName.isNotEmpty) ...[
                const SizedBox(height: 5),
                Row(
                  children: [
                    const Icon(
                      Icons.person_outline,
                      size: 13,
                      color: AppColors.mutedLight,
                    ),
                    const SizedBox(width: 4),
                    Expanded(
                      child: Text(
                        lead.contactName,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 12,
                          color: AppColors.muted,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
              if (lead.phone.isNotEmpty) ...[
                const SizedBox(height: 3),
                Row(
                  children: [
                    const Icon(
                      Icons.phone_outlined,
                      size: 13,
                      color: AppColors.mutedLight,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      lead.phone,
                      style: const TextStyle(
                        fontSize: 12,
                        color: AppColors.muted,
                      ),
                    ),
                  ],
                ),
              ],
              if (lead.targetPropertyName.isNotEmpty) ...[
                const SizedBox(height: 3),
                Row(
                  children: [
                    const Icon(
                      Icons.home_outlined,
                      size: 13,
                      color: AppColors.mutedLight,
                    ),
                    const SizedBox(width: 4),
                    Expanded(
                      child: Text(
                        lead.targetPropertyName,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 12,
                          color: AppColors.muted,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
              const SizedBox(height: 9),
              Row(
                children: [
                  AppBadge(
                    label: LeadScoreStyle.label(lead.leadScore),
                    color: LeadScoreStyle.color(lead.leadScore),
                  ),
                  const Spacer(),
                  if (lead.clientBudget > 0)
                    Text(
                      currency.format(lead.clientBudget),
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 12.5,
                        color: AppColors.navy,
                      ),
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
