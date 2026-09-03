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

class LeadFunnelScreen extends StatefulWidget {
  final bool isPostSale;
  const LeadFunnelScreen({super.key, this.isPostSale = false});

  @override
  State<LeadFunnelScreen> createState() => _LeadFunnelScreenState();
}

class _AdvisorOption {
  final int id;
  final String name;
  const _AdvisorOption({required this.id, required this.name});
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

  int? _selectedAdvisorId;
  List<_AdvisorOption> _advisors = [];

  @override
  void initState() {
    super.initState();
    final auth = context.read<AuthService>();
    final odoo = auth.odoo;
    _leadService = LeadService(odoo);
    _stageService = CrmStageService(odoo);

    if (!auth.isAdmin) {
      _selectedAdvisorId = 0;
    } else {
      _loadAdvisors();
    }
    _load();
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  Future<void> _loadAdvisors() async {
    try {
      final odoo = context.read<AuthService>().odoo;
      final rows = await odoo.searchRead(
        model: 'res.users',
        domain: [
          ['share', '=', false],
        ],
        fields: ['name'],
        order: 'name asc',
        limit: 60,
      );
      if (mounted) {
        setState(() {
          _advisors = rows
              .map(
                (r) => _AdvisorOption(
                  id: r['id'] as int,
                  name: r['name'] as String,
                ),
              )
              .toList();
        });
      }
    } catch (_) {}
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final auth = context.read<AuthService>();
      final isAdm = auth.isAdmin;
      final stages = await _stageService.list(isPostSale: widget.isPostSale);

      final bool myLeadsOnly = (!isAdm || _selectedAdvisorId == 0);
      final int? advisorFilter =
          (isAdm && _selectedAdvisorId != null && _selectedAdvisorId! > 0)
          ? _selectedAdvisorId
          : null;

      final leads = await _leadService.list(
        limit: 300,
        myLeadsOnly: myLeadsOnly,
        currentUserId: auth.odoo.userId,
        advisorId: advisorFilter,
      );
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

  int get _totalLeadsCount {
    int count = 0;
    for (final list in _leadsByStage.values) {
      count += list.length;
    }
    return count;
  }

  String get _currentAdvisorLabel {
    if (_selectedAdvisorId == null) return 'Todos los Asesores';
    if (_selectedAdvisorId == 0) return 'Mis Leads';
    final match = _advisors.where((a) => a.id == _selectedAdvisorId);
    return match.isNotEmpty ? match.first.name : 'Asesor';
  }

  Future<void> _showAdvisorPicker() async {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colors = AppColors.of(context);
    await showModalBottomSheet(
      context: context,
      backgroundColor: isDark ? const Color(0xFF14112E) : Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const SizedBox(height: 12),
              Center(
                child: Container(
                  width: 36,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.grey[400],
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const Padding(
                padding: EdgeInsets.fromLTRB(20, 14, 20, 10),
                child: Row(
                  children: [
                    Icon(
                      Icons.people_alt_rounded,
                      size: 18,
                      color: Color(0xFF28235D),
                    ),
                    SizedBox(width: 8),
                    Text(
                      'Filtrar Embudo por Asesor',
                      style: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ],
                ),
              ),
              const Divider(height: 1),
              Expanded(
                child: ListView(
                  children: [
                    ListTile(
                      leading: const Icon(
                        Icons.public_rounded,
                        color: Color(0xFF28235D),
                      ),
                      title: const Text(
                        'Todos los Asesores (Toda la Inmobiliaria)',
                        style: TextStyle(
                          fontWeight: FontWeight.w600,
                          fontSize: 13.5,
                        ),
                      ),
                      trailing: _selectedAdvisorId == null
                          ? const Icon(
                              Icons.check_circle_rounded,
                              color: Color(0xFFD81F26),
                            )
                          : null,
                      onTap: () {
                        Navigator.pop(ctx);
                        setState(() => _selectedAdvisorId = null);
                        _load();
                      },
                    ),
                    ListTile(
                      leading: const Icon(
                        Icons.person_rounded,
                        color: Color(0xFFD81F26),
                      ),
                      title: const Text(
                        'Mis Leads Asignados',
                        style: TextStyle(
                          fontWeight: FontWeight.w600,
                          fontSize: 13.5,
                        ),
                      ),
                      trailing: _selectedAdvisorId == 0
                          ? const Icon(
                              Icons.check_circle_rounded,
                              color: Color(0xFFD81F26),
                            )
                          : null,
                      onTap: () {
                        Navigator.pop(ctx);
                        setState(() => _selectedAdvisorId = 0);
                        _load();
                      },
                    ),
                    if (_advisors.isNotEmpty) ...[
                      Padding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 8,
                        ),
                        child: Text(
                          'EQUIPO COMERCIAL',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 0.5,
                            color: colors.muted,
                          ),
                        ),
                      ),
                      ..._advisors.map(
                        (adv) => ListTile(
                          leading: CircleAvatar(
                            radius: 14,
                            backgroundColor: const Color(
                              0xFF28235D,
                            ).withValues(alpha: 0.1),
                            child: Text(
                              adv.name.isNotEmpty
                                  ? adv.name[0].toUpperCase()
                                  : 'A',
                              style: const TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                                color: Color(0xFF28235D),
                              ),
                            ),
                          ),
                          title: Text(
                            adv.name,
                            style: const TextStyle(fontSize: 13.5),
                          ),
                          trailing: _selectedAdvisorId == adv.id
                              ? const Icon(
                                  Icons.check_circle_rounded,
                                  color: Color(0xFFD81F26),
                                )
                              : null,
                          onTap: () {
                            Navigator.pop(ctx);
                            setState(() => _selectedAdvisorId = adv.id);
                            _load();
                          },
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
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
    final auth = context.watch<AuthService>();
    final isAdmin = auth.isAdmin;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colors = AppColors.of(context);

    return Scaffold(
      floatingActionButton: Padding(
        padding: const EdgeInsets.only(bottom: 74),
        child: FloatingActionButton.small(
          heroTag: null,
          onPressed: _openCreate,
          elevation: 4,
          backgroundColor: const Color(0xFFD81F26),
          tooltip: 'Nuevo Lead',
          child: const Icon(
            Icons.person_add_alt_1_rounded,
            color: Colors.white,
            size: 20,
          ),
        ),
      ),
      body: Column(
        children: [
          if (isAdmin)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 7),
              decoration: BoxDecoration(
                color: isDark
                    ? const Color(0xFF1E1A3E)
                    : const Color(0xFFF8FAFC),
                border: Border(
                  bottom: BorderSide(
                    color: isDark ? Colors.white12 : const Color(0xFFE2E8F0),
                  ),
                ),
              ),
              child: Row(
                children: [
                  InkWell(
                    onTap: _showAdvisorPicker,
                    borderRadius: BorderRadius.circular(8),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 5,
                      ),
                      decoration: BoxDecoration(
                        color: isDark ? const Color(0xFF0F172A) : Colors.white,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: const Color(
                            0xFFD81F26,
                          ).withValues(alpha: 0.35),
                          width: 1.2,
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(
                            Icons.person_search_rounded,
                            size: 15,
                            color: Color(0xFFD81F26),
                          ),
                          const SizedBox(width: 6),
                          Text(
                            _currentAdvisorLabel,
                            style: const TextStyle(
                              fontSize: 12.5,
                              fontWeight: FontWeight.w800,
                              color: Color(0xFF28235D),
                            ),
                          ),
                          const SizedBox(width: 4),
                          const Icon(
                            Icons.arrow_drop_down_rounded,
                            size: 18,
                            color: Color(0xFFD81F26),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const Spacer(),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: const Color(0xFF28235D).withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      '$_totalLeadsCount ${_totalLeadsCount == 1 ? 'lead' : 'leads'}',
                      style: const TextStyle(
                        fontSize: 11.5,
                        fontWeight: FontWeight.w800,
                        color: Color(0xFF28235D),
                      ),
                    ),
                  ),
                ],
              ),
            )
          else
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
              decoration: BoxDecoration(
                color: isDark
                    ? const Color(0xFF1E1A3E)
                    : const Color(0xFFF8FAFC),
                border: Border(
                  bottom: BorderSide(
                    color: isDark ? Colors.white12 : const Color(0xFFE2E8F0),
                  ),
                ),
              ),
              child: Row(
                children: [
                  const Icon(
                    Icons.person_pin_rounded,
                    size: 15,
                    color: Color(0xFFD81F26),
                  ),
                  const SizedBox(width: 6),
                  const Text(
                    'Mis Oportunidades Asignadas',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: Color(0xFF28235D),
                    ),
                  ),
                  const Spacer(),
                  Text(
                    '$_totalLeadsCount ${_totalLeadsCount == 1 ? 'lead' : 'leads'}',
                    style: TextStyle(
                      fontSize: 11.5,
                      fontWeight: FontWeight.w700,
                      color: colors.muted,
                    ),
                  ),
                ],
              ),
            ),

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
                    color: i == _currentPage ? colors.navy : colors.line,
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
    final colors = AppColors.of(context);
    final total = leads.fold<double>(0, (sum, l) => sum + l.clientBudget);
    final accent = stage.isLost ? colors.danger : colors.navy;

    return Container(
      margin: const EdgeInsets.fromLTRB(8, 10, 8, 0),
      decoration: BoxDecoration(
        color: colors.neutralBg,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        children: [
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
                          style: TextStyle(
                            fontSize: 12,
                            color: colors.muted,
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
                ? Center(
                    child: Text(
                      'Sin oportunidades\nen esta etapa',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: colors.mutedLight,
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
    final colors = AppColors.of(context);
    return Material(
      color: colors.surface,
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
                    color: LeadTemperatureStyle.color(
                      lead.leadTemperature,
                      colors,
                    ),
                  ),
                ],
              ),
              if (lead.contactName.isNotEmpty) ...[
                const SizedBox(height: 5),
                Row(
                  children: [
                    Icon(
                      Icons.person_outline,
                      size: 13,
                      color: colors.mutedLight,
                    ),
                    const SizedBox(width: 4),
                    Expanded(
                      child: Text(
                        lead.contactName,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 12, color: colors.muted),
                      ),
                    ),
                  ],
                ),
              ],
              if (lead.phone.isNotEmpty) ...[
                const SizedBox(height: 3),
                Row(
                  children: [
                    Icon(
                      Icons.phone_outlined,
                      size: 13,
                      color: colors.mutedLight,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      lead.phone,
                      style: TextStyle(fontSize: 12, color: colors.muted),
                    ),
                  ],
                ),
              ],
              if (lead.targetPropertyName.isNotEmpty) ...[
                const SizedBox(height: 3),
                Row(
                  children: [
                    Icon(
                      Icons.home_outlined,
                      size: 13,
                      color: colors.mutedLight,
                    ),
                    const SizedBox(width: 4),
                    Expanded(
                      child: Text(
                        lead.targetPropertyName,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 12, color: colors.muted),
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
                    color: LeadScoreStyle.color(lead.leadScore, colors),
                  ),
                  const Spacer(),
                  if (lead.clientBudget > 0)
                    Text(
                      currency.format(lead.clientBudget),
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 12.5,
                        color: colors.navy,
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
