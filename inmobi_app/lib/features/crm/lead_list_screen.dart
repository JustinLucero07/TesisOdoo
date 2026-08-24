import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/app_badge.dart';
import '../../core/widgets/states.dart';
import '../../core/widgets/skeleton.dart';
import '../auth/auth_service.dart';
import '../visits/visit_form_screen.dart';
import 'crm_stage_service.dart';
import 'lead_detail_screen.dart';
import 'lead_form_screen.dart';
import 'lead_model.dart';
import 'lead_service.dart';

class LeadListScreen extends StatefulWidget {
  final bool isPostSale;
  const LeadListScreen({super.key, this.isPostSale = false});

  @override
  State<LeadListScreen> createState() => _LeadListScreenState();
}

class _LeadListScreenState extends State<LeadListScreen> {
  late final LeadService _service;
  late final CrmStageService _stageService;
  final _searchCtrl = TextEditingController();

  String? _temperatureFilter;
  int? _stageFilter;
  bool _myLeadsOnly = false;
  double? _minBudget;
  double? _maxBudget;
  int? _priority;
  String _sortOrder = 'lead_temperature desc, write_date desc';
  List<CrmStage> _stages = [];

  List<Lead> _leads = [];
  bool _loading = true;
  String? _error;

  int get _activeLeadFilterCount {
    int count = 0;
    if (_myLeadsOnly) count++;
    if (_minBudget != null && _minBudget! > 0) count++;
    if (_maxBudget != null && _maxBudget! > 0) count++;
    if (_priority != null && _priority! > 0) count++;
    if (_stageFilter != null) count++;
    return count;
  }

  static const _filters = [
    (null, 'Todos'),
    ('boiling', '¡Hirviendo!'),
    ('hot', 'Caliente'),
    ('warm', 'Tibio'),
    ('cold', 'Frío'),
  ];

  static const _sortOptions = [
    ('lead_temperature desc, write_date desc', 'Mayor Temperatura'),
    ('client_budget desc', 'Mayor Presupuesto'),
    ('date_deadline asc', 'Cierre Próximo'),
    ('write_date desc', 'Última Actividad'),
  ];

  @override
  void initState() {
    super.initState();
    final odoo = context.read<AuthService>().odoo;
    _service = LeadService(odoo);
    _stageService = CrmStageService(odoo);
    _stageService.list(isPostSale: widget.isPostSale).then((s) {
      if (mounted) setState(() => _stages = s);
    });
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final auth = context.read<AuthService>();
      if (_stages.isEmpty) {
        _stages = await _stageService.list(isPostSale: widget.isPostSale);
      }
      final result = await _service.list(
        searchText: _searchCtrl.text,
        temperature: _temperatureFilter,
        stageId: _stageFilter,
        myLeadsOnly: _myLeadsOnly,
        currentUserId: auth.odoo.userId,
        minBudget: _minBudget,
        maxBudget: _maxBudget,
        priority: _priority,
        order: _sortOrder,
      );
      final stageIds = _stages.map((s) => s.id).toSet();
      if (stageIds.isNotEmpty) {
        setState(() => _leads = result.where((l) => l.stageId != null && stageIds.contains(l.stageId)).toList());
      } else {
        setState(() => _leads = result);
      }
    } catch (e) {
      setState(() => _error = 'No se pudieron cargar los leads.');
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

  void _openLeadFilterModal() {
    HapticFeedback.lightImpact();
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => _LeadFilterSheet(
        myLeadsOnly: _myLeadsOnly,
        minBudget: _minBudget,
        maxBudget: _maxBudget,
        priority: _priority,
        stageId: _stageFilter,
        stages: _stages,
        onApply: (myOnly, minB, maxB, prio, stg) {
          setState(() {
            _myLeadsOnly = myOnly;
            _minBudget = minB;
            _maxBudget = maxB;
            _priority = prio;
            _stageFilter = stg;
          });
          _load();
        },
      ),
    );
  }

  void _showSortPicker() {
    HapticFeedback.lightImpact();
    final isDark = Theme.of(context).brightness == Brightness.dark;
    showModalBottomSheet(
      context: context,
      backgroundColor: isDark ? const Color(0xFF14112E) : Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 20, vertical: 8),
                  child: Text(
                    'Ordenar Oportunidades',
                    style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800),
                  ),
                ),
                const Divider(height: 1),
                ..._sortOptions.map((opt) {
                  final (value, label) = opt;
                  final selected = _sortOrder == value;
                  return ListTile(
                    leading: Icon(
                      selected ? Icons.radio_button_checked : Icons.radio_button_off,
                      color: selected ? const Color(0xFF28235D) : AppColors.muted,
                      size: 20,
                    ),
                    title: Text(
                      label,
                      style: TextStyle(
                        fontWeight: selected ? FontWeight.w800 : FontWeight.w500,
                        color: selected ? const Color(0xFF28235D) : null,
                      ),
                    ),
                    selected: selected,
                    selectedTileColor: const Color(0xFF28235D).withValues(alpha: 0.08),
                    onTap: () {
                      setState(() => _sortOrder = value);
                      Navigator.pop(ctx);
                      _load();
                    },
                  );
                }),
              ],
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final currency = NumberFormat.currency(
      locale: 'es_EC',
      symbol: '\$',
      decimalDigits: 0,
    );
    final isDark = Theme.of(context).brightness == Brightness.dark;

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
      body: RefreshIndicator(
        onRefresh: _load,
        child: Column(
          children: [
            // Barra de búsqueda con orden y botón +
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 6),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _searchCtrl,
                      decoration: InputDecoration(
                        hintText: 'Buscar lead o contacto...',
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

                  // Botón de Ordenamiento
                  Tooltip(
                    message: 'Ordenar',
                    child: Material(
                      color: isDark ? const Color(0xFF1E1A3E) : const Color(0xFFF1F5F9),
                      borderRadius: BorderRadius.circular(14),
                      child: InkWell(
                        borderRadius: BorderRadius.circular(14),
                        onTap: _showSortPicker,
                        child: Container(
                          width: 44,
                          height: 44,
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(14),
                            border: Border.all(
                              color: isDark ? Colors.white12 : const Color(0xFFE2E8F0),
                            ),
                          ),
                          child: const Icon(
                            Icons.sort_rounded,
                            size: 20,
                            color: Color(0xFF28235D),
                          ),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),

                  // Botón de Filtros Avanzados con Badge
                  Tooltip(
                    message: 'Filtros Avanzados',
                    child: Stack(
                      clipBehavior: Clip.none,
                      children: [
                        Material(
                          color: _activeLeadFilterCount > 0
                              ? const Color(0xFF28235D)
                              : (isDark ? const Color(0xFF1E1A3E) : const Color(0xFFF1F5F9)),
                          borderRadius: BorderRadius.circular(14),
                          child: InkWell(
                            borderRadius: BorderRadius.circular(14),
                            onTap: _openLeadFilterModal,
                            child: Container(
                              width: 44,
                              height: 44,
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(14),
                                border: Border.all(
                                  color: _activeLeadFilterCount > 0
                                      ? const Color(0xFF28235D)
                                      : (isDark ? Colors.white12 : const Color(0xFFE2E8F0)),
                                ),
                              ),
                              child: Icon(
                                Icons.tune_rounded,
                                size: 20,
                                color: _activeLeadFilterCount > 0
                                    ? Colors.white
                                    : const Color(0xFF28235D),
                              ),
                            ),
                          ),
                        ),
                        if (_activeLeadFilterCount > 0)
                          Positioned(
                            top: -4,
                            right: -4,
                            child: Container(
                              padding: const EdgeInsets.all(5),
                              decoration: const BoxDecoration(
                                color: Color(0xFFD81F26),
                                shape: BoxShape.circle,
                              ),
                              child: Text(
                                '$_activeLeadFilterCount',
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 10,
                                  fontWeight: FontWeight.w800,
                                  height: 1,
                                ),
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),

                  // Botón de Creación Rápida
                  Tooltip(
                    message: 'Nuevo Lead',
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
                            Icons.add_rounded,
                            color: Colors.white,
                            size: 22,
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),

            // Chips de Temperatura
            SizedBox(
              height: 44,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                itemCount: _filters.length,
                separatorBuilder: (_, _) => const SizedBox(width: 8),
                itemBuilder: (context, i) {
                  final (value, label) = _filters[i];
                  final selected = _temperatureFilter == value;
                  return ChoiceChip(
                    label: Text(label),
                    selected: selected,
                    selectedColor: AppColors.navy,
                    labelStyle: TextStyle(
                      color: selected ? Colors.white : AppColors.ink,
                      fontWeight: FontWeight.w600,
                      fontSize: 12.5,
                    ),
                    side: BorderSide.none,
                    showCheckmark: false,
                    onSelected: (_) {
                      setState(() => _temperatureFilter = value);
                      _load();
                    },
                  );
                },
              ),
            ),

            // Chips de Etapas
            if (_stages.isNotEmpty)
              SizedBox(
                height: 40,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                  itemCount: _stages.length + 1,
                  separatorBuilder: (_, _) => const SizedBox(width: 8),
                  itemBuilder: (context, i) {
                    final stageId = i == 0 ? null : _stages[i - 1].id;
                    final label = i == 0 ? 'Todas las etapas' : _stages[i - 1].name;
                    final selected = _stageFilter == stageId;
                    return ChoiceChip(
                      label: Text(label),
                      selected: selected,
                      selectedColor: isDark ? AppColors.navyLight : AppColors.navy,
                      backgroundColor: isDark ? const Color(0xFF1E1A3E) : AppColors.neutralBg,
                      labelStyle: TextStyle(
                        color: selected ? Colors.white : (isDark ? Colors.white70 : AppColors.ink),
                        fontWeight: FontWeight.w600,
                        fontSize: 12,
                      ),
                      side: BorderSide.none,
                      showCheckmark: false,
                      onSelected: (_) {
                        setState(() => _stageFilter = stageId);
                        _load();
                      },
                    );
                  },
                ),
              ),

            // Contador de resultados
            if (!_loading && _error == null && _leads.isNotEmpty)
              Padding(
                padding: const EdgeInsets.fromLTRB(18, 4, 18, 4),
                child: Row(
                  children: [
                    Text(
                      '${_leads.length} ${_leads.length == 1 ? 'oportunidad' : 'oportunidades'}',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                      ),
                    ),
                  ],
                ),
              ),

            const SizedBox(height: 4),
            Expanded(child: _buildBody(currency)),
          ],
        ),
      ),
    );
  }

  Widget _buildBody(NumberFormat currency) {
    if (_loading) return const SkeletonList();
    if (_error != null) {
      return MessageView(
        icon: Icons.error_outline,
        message: _error!,
        onRetry: _load,
      );
    }
    if (_leads.isEmpty) {
      return const MessageView(
        icon: Icons.people_outline,
        message: 'No se encontraron leads.',
      );
    }
    return LayoutBuilder(
      builder: (context, constraints) {
        final w = constraints.maxWidth;
        final cols = w >= 700 ? 2 : 1;

        if (cols == 1) {
          return ListView.separated(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 110),
            itemCount: _leads.length,
            separatorBuilder: (_, _) => const SizedBox(height: 12),
            itemBuilder: (context, i) => _buildLeadCard(_leads[i], currency),
          );
        }

        return GridView.builder(
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 110),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 2,
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
            mainAxisExtent: 180,
          ),
          itemCount: _leads.length,
          itemBuilder: (context, i) => _buildLeadCard(_leads[i], currency),
        );
      },
    );
  }

  Widget _buildLeadCard(Lead lead, NumberFormat currency) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final tempColor = LeadTemperatureStyle.color(lead.leadTemperature);

    return Dismissible(
      key: ValueKey('lead_${lead.id}'),
      direction: DismissDirection.horizontal,
      confirmDismiss: (direction) async {
        HapticFeedback.mediumImpact();
        if (direction == DismissDirection.startToEnd) {
          // Swipe Derecha -> Contactar por WhatsApp
          final phone = (lead.phone.isNotEmpty ? lead.phone : lead.contactName).replaceAll(RegExp(r'[^0-9+]'), '');
          final clientName = lead.contactName.isNotEmpty ? lead.contactName : 'Estimado/a';
          final msg = Uri.encodeComponent('Hola $clientName, te saludo de Inmobi Inmobiliaria respecto a tu consulta.');
          final url = Uri.parse('https://wa.me/$phone?text=$msg');
          if (await canLaunchUrl(url)) {
            await launchUrl(url, mode: LaunchMode.externalApplication);
          } else {
            if (mounted) {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('No se pudo abrir WhatsApp o no hay número registrado.')),
              );
            }
          }
        } else if (direction == DismissDirection.endToStart) {
          // Swipe Izquierda -> Agendar Visita directa
          if (mounted) {
            Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => VisitFormScreen(
                  initialClientId: lead.partnerId,
                  initialClientName: lead.partnerName.isNotEmpty ? lead.partnerName : lead.contactName,
                  initialPropertyId: lead.targetPropertyId,
                  initialPropertyName: lead.targetPropertyName,
                ),
              ),
            ).then((_) => _load());
          }
        }
        return false;
      },
      background: Container(
        alignment: Alignment.centerLeft,
        padding: const EdgeInsets.symmetric(horizontal: 20),
        decoration: BoxDecoration(
          color: const Color(0xFF25D366),
          borderRadius: BorderRadius.circular(20),
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
          borderRadius: BorderRadius.circular(20),
        ),
        child: const Row(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            Text(
              'Agendar Cita',
              style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 13),
            ),
            SizedBox(width: 8),
            Icon(Icons.calendar_month_outlined, color: Colors.white, size: 22),
          ],
        ),
      ),
      child: Container(
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF1E1A3E) : Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isDark ? Colors.white12 : AppColors.line,
          ),
          boxShadow: softShadow(opacity: isDark ? 0.25 : 0.04, isDark: isDark),
        ),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: BorderRadius.circular(20),
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => LeadDetailScreen(leadId: lead.id),
              ),
            ).then((_) => _load()),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  InitialsAvatar(
                    text: lead.contactName.isNotEmpty
                        ? lead.contactName
                        : lead.name,
                    size: 46,
                    color: tempColor,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                lead.contactName.isNotEmpty
                                    ? lead.contactName
                                    : lead.name,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w800,
                                  fontSize: 14.5,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            const SizedBox(width: 6),
                            AppBadge(
                              label: LeadTemperatureStyle.label(
                                lead.leadTemperature,
                              ),
                              color: tempColor,
                              background: tempColor.withValues(alpha: 0.12),
                              icon: LeadTemperatureStyle.icon(
                                lead.leadTemperature,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 3),
                        Text(
                          lead.name,
                          style: TextStyle(
                            fontSize: 12.5,
                            color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                            fontWeight: FontWeight.w500,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        if (lead.targetPropertyName.isNotEmpty) ...[
                          const SizedBox(height: 6),
                          Row(
                            children: [
                              const Icon(
                                Icons.home_work_outlined,
                                size: 14,
                                color: Color(0xFFD81F26),
                              ),
                              const SizedBox(width: 4),
                              Expanded(
                                child: Text(
                                  lead.targetPropertyName,
                                  style: const TextStyle(
                                    fontSize: 12,
                                    color: AppColors.ink,
                                    fontWeight: FontWeight.w600,
                                  ),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                            ],
                          ),
                        ],
                        if (lead.clientBudget > 0) ...[
                          const SizedBox(height: 6),
                          Text(
                            'Presupuesto: ${currency.format(lead.clientBudget)}',
                            style: const TextStyle(
                              fontSize: 12.5,
                              fontWeight: FontWeight.w700,
                              color: Color(0xFF28235D),
                            ),
                          ),
                        ],
                        const SizedBox(height: 8),
                        Wrap(
                          spacing: 6,
                          runSpacing: 4,
                          children: [
                            if (lead.matchPercentage > 0)
                              AppBadge(
                                label: '${lead.matchPercentage}% Match',
                                color: AppColors.success,
                                background: AppColors.success.withValues(
                                  alpha: 0.1,
                                ),
                              ),
                            if (lead.stageName.isNotEmpty)
                              AppBadge(
                                label: lead.stageName,
                                color: AppColors.navy,
                                background: AppColors.navy.withValues(alpha: 0.08),
                              ),
                            if (lead.leadSourceName.isNotEmpty)
                              AppBadge(
                                label: lead.leadSourceName,
                                color: AppColors.muted,
                                background: AppColors.neutralBg,
                              ),
                          ],
                        ),
                      ],
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

/// Hoja modal de filtros avanzados para Leads y Oportunidades del CRM
class _LeadFilterSheet extends StatefulWidget {
  final bool myLeadsOnly;
  final double? minBudget;
  final double? maxBudget;
  final int? priority;
  final int? stageId;
  final List<CrmStage> stages;
  final Function(bool, double?, double?, int?, int?) onApply;

  const _LeadFilterSheet({
    required this.myLeadsOnly,
    required this.minBudget,
    required this.maxBudget,
    required this.priority,
    required this.stageId,
    required this.stages,
    required this.onApply,
  });

  @override
  State<_LeadFilterSheet> createState() => _LeadFilterSheetState();
}

class _LeadFilterSheetState extends State<_LeadFilterSheet> {
  late bool _myLeadsOnly;
  late final TextEditingController _minBudgetCtrl;
  late final TextEditingController _maxBudgetCtrl;
  int? _priority;
  int? _stageId;

  @override
  void initState() {
    super.initState();
    _myLeadsOnly = widget.myLeadsOnly;
    _minBudgetCtrl = TextEditingController(
      text: widget.minBudget != null ? widget.minBudget!.toInt().toString() : '',
    );
    _maxBudgetCtrl = TextEditingController(
      text: widget.maxBudget != null ? widget.maxBudget!.toInt().toString() : '',
    );
    _priority = widget.priority;
    _stageId = widget.stageId;
  }

  @override
  void dispose() {
    _minBudgetCtrl.dispose();
    _maxBudgetCtrl.dispose();
    super.dispose();
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
                    'Filtros de Oportunidades',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  TextButton(
                    onPressed: () {
                      setState(() {
                        _myLeadsOnly = false;
                        _minBudgetCtrl.clear();
                        _maxBudgetCtrl.clear();
                        _priority = null;
                        _stageId = null;
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

              // 1. Asesor Asignado
              Container(
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF1E1A3E) : const Color(0xFFF8FAFC),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: isDark ? Colors.white12 : const Color(0xFFE2E8F0),
                  ),
                ),
                child: SwitchListTile.adaptive(
                  activeTrackColor: const Color(0xFF28235D),
                  activeThumbColor: Colors.white,
                  title: const Text(
                    'Solo mis Oportunidades',
                    style: TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700),
                  ),
                  subtitle: const Text(
                    'Mostrar únicamente leads asignados a mi usuario',
                    style: TextStyle(fontSize: 11.5, color: AppColors.muted),
                  ),
                  value: _myLeadsOnly,
                  onChanged: (v) => setState(() => _myLeadsOnly = v),
                ),
              ),
              const SizedBox(height: 16),

              // 2. Rango de Presupuesto del Cliente
              const Text(
                'Presupuesto del Cliente (\$ USD)',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _minBudgetCtrl,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        hintText: 'Presupuesto mín.',
                        prefixText: '\$ ',
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextField(
                      controller: _maxBudgetCtrl,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        hintText: 'Presupuesto máx.',
                        prefixText: '\$ ',
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // 3. Prioridad / Importancia
              const Text(
                'Nivel de Prioridad',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  _LeadOptionButton(
                    label: 'Todas',
                    selected: _priority == null,
                    onTap: () => setState(() => _priority = null),
                  ),
                  const SizedBox(width: 8),
                  ...[1, 2, 3].map((p) {
                    final stars = '★' * p;
                    return Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: _LeadOptionButton(
                        label: stars,
                        selected: _priority == p,
                        onTap: () => setState(() => _priority = p),
                      ),
                    );
                  }),
                ],
              ),
              const SizedBox(height: 16),

              // 4. Etapa del Embudo
              if (widget.stages.isNotEmpty) ...[
                const Text(
                  'Etapa del Embudo',
                  style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 8),
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      _LeadOptionButton(
                        label: 'Cualquiera',
                        selected: _stageId == null,
                        onTap: () => setState(() => _stageId = null),
                      ),
                      const SizedBox(width: 8),
                      ...widget.stages.map((stg) {
                        return Padding(
                          padding: const EdgeInsets.only(right: 8),
                          child: _LeadOptionButton(
                            label: stg.name,
                            selected: _stageId == stg.id,
                            onTap: () => setState(() => _stageId = stg.id),
                          ),
                        );
                      }),
                    ],
                  ),
                ),
                const SizedBox(height: 22),
              ],

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
                    final minB = double.tryParse(_minBudgetCtrl.text.trim());
                    final maxB = double.tryParse(_maxBudgetCtrl.text.trim());
                    widget.onApply(
                      _myLeadsOnly,
                      minB,
                      maxB,
                      _priority,
                      _stageId,
                    );
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

class _LeadOptionButton extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _LeadOptionButton({
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
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
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
