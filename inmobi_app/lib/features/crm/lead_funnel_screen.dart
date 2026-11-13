import 'dart:async';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/add_button.dart';
import '../../core/widgets/app_badge.dart';
import '../../core/widgets/states.dart';
import '../auth/auth_service.dart';
import '../reminders/lead_reminder.dart';
import 'crm_stage_service.dart';
import 'lead_detail_screen.dart';
import 'lead_form_screen.dart';
import 'lead_model.dart';
import 'lead_service.dart';
import '../../core/utils/formats.dart';

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
  // Total real de cada etapa: las columnas cargan de a 40 al ir bajando.
  Map<int, int> _countByStage = {};
  final Set<int> _loadingMore = {};
  bool _openedOnce = false;
  static const _pageSize = 40;
  bool _loading = true;
  String? _error;
  int _currentPage = 0;

  int? _selectedAdvisorId;
  List<_AdvisorOption> _advisors = [];

  final _searchCtrl = TextEditingController();
  Timer? _debounce;
  String _query = '';
  // Cada búsqueda lleva un número: si una respuesta vieja llega después de
  // una nueva, se descarta en vez de pisar los resultados.
  int _loadSeq = 0;

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
    _searchCtrl.dispose();
    _debounce?.cancel();
    super.dispose();
  }

  void _onSearchChanged(String value) {
    setState(() {});
    _debounce?.cancel();
    // Se espera a que deje de escribir para no lanzar una consulta por letra.
    _debounce = Timer(const Duration(milliseconds: 400), () {
      final q = value.trim();
      if (q == _query) return;
      _query = q;
      _load();
    });
  }

  void _clearSearch() {
    _debounce?.cancel();
    _searchCtrl.clear();
    if (_query.isEmpty) {
      setState(() {});
      return;
    }
    _query = '';
    _load();
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
    final pedido = ++_loadSeq;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final auth = context.read<AuthService>();
      final stages = await _stageService.list(isPostSale: widget.isPostSale);

      // Se respeta lo elegido en el selector. Quién puede ver los leads de
      // otros lo deciden las reglas de registro de Odoo en el servidor;
      // forzar aquí "solo mis leads" dejaba el embudo vacío cuando la app
      // no reconocía al usuario como administrador.
      final bool myLeadsOnly = _selectedAdvisorId == 0;
      final int? advisorFilter =
          (_selectedAdvisorId != null && _selectedAdvisorId! > 0)
          ? _selectedAdvisorId
          : null;

      // Cada columna pide sus propios leads. Antes se traían 300 de una sola
      // consulta y se repartían aquí: con más leads que ese tope, las etapas
      // con pocos registros o poco recientes quedaban vacías aunque en Odoo
      // sí tuvieran leads.
      final conteos = Future.wait(
        stages.map(
          (s) => _leadService.count(
            myLeadsOnly: myLeadsOnly,
            currentUserId: auth.odoo.userId,
            advisorId: advisorFilter,
            stageId: s.id,
            searchText: _query,
          ),
        ),
      );
      final porEtapa = await Future.wait(
        stages.map(
          (s) => _leadService.list(
            limit: _pageSize,
            myLeadsOnly: myLeadsOnly,
            currentUserId: auth.odoo.userId,
            advisorId: advisorFilter,
            stageId: s.id,
            searchText: _query,
          ),
        ),
      );
      final totales = await conteos;
      final grouped = <int, List<Lead>>{};
      final counts = <int, int>{};
      for (var i = 0; i < stages.length; i++) {
        grouped[stages[i].id] = porEtapa[i];
        counts[stages[i].id] = totales[i];
      }
      if (!mounted || pedido != _loadSeq) return;
      setState(() {
        _stages = stages;
        _leadsByStage = grouped;
        _countByStage = counts;
        _loadingMore.clear();
      });
      // Al buscar, y al abrir el embudo, se salta a la primera etapa con
      // leads: si no, la primera columna (p. ej. "Oportunidades Bot") podía
      // salir vacía y parecer que no había nada.
      final primeraCarga = !_openedOnce;
      _openedOnce = true;
      final actualVacia =
          _currentPage >= stages.length ||
          (grouped[stages[_currentPage].id] ?? const <Lead>[]).isEmpty;
      if (_query.isNotEmpty || (primeraCarga && actualVacia)) {
        final idx = stages.indexWhere(
          (st) => (grouped[st.id] ?? const <Lead>[]).isNotEmpty,
        );
        if (idx >= 0) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (_pageController.hasClients) {
              _pageController.animateToPage(
                idx,
                duration: const Duration(milliseconds: 280),
                curve: Curves.easeOutCubic,
              );
            }
          });
        }
      }
    } catch (e) {
      if (!mounted || pedido != _loadSeq) return;
      if (_stages.isEmpty) {
        setState(() => _error = 'No se pudo cargar el embudo.');
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No se pudo completar la búsqueda.')),
        );
      }
    } finally {
      if (mounted && pedido == _loadSeq) setState(() => _loading = false);
    }
  }

  int get _totalLeadsCount {
    int count = 0;
    for (final stage in _stages) {
      count += _countByStage[stage.id] ?? _leadsByStage[stage.id]?.length ?? 0;
    }
    return count;
  }

  /// Trae los siguientes leads de una columna al llegar al final de la lista.
  Future<void> _loadMore(int stageId) async {
    final current = _leadsByStage[stageId] ?? const <Lead>[];
    final total = _countByStage[stageId] ?? current.length;
    if (_loadingMore.contains(stageId) || current.length >= total) return;
    final pedido = _loadSeq;
    setState(() => _loadingMore.add(stageId));
    try {
      final auth = context.read<AuthService>();
      final more = await _leadService.list(
        limit: _pageSize,
        offset: current.length,
        myLeadsOnly: _selectedAdvisorId == 0,
        currentUserId: auth.odoo.userId,
        advisorId: (_selectedAdvisorId != null && _selectedAdvisorId! > 0)
            ? _selectedAdvisorId
            : null,
        stageId: stageId,
        searchText: _query,
      );
      if (!mounted || pedido != _loadSeq) return;
      final ids = current.map((l) => l.id).toSet();
      setState(() {
        _leadsByStage[stageId] = [
          ...current,
          ...more.where((l) => !ids.contains(l.id)),
        ];
        if (more.isEmpty) _countByStage[stageId] = current.length;
      });
    } catch (_) {
      // Si falla, se puede volver a intentar bajando otra vez.
    } finally {
      if (mounted) setState(() => _loadingMore.remove(stageId));
    }
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
                      color: AppColors.navy,
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
                        color: AppColors.navy,
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
                              color: AppColors.accent,
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
                        color: AppColors.accent,
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
                              color: AppColors.accent,
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
                            backgroundColor: AppColors.navy.withValues(
                              alpha: 0.1,
                            ),
                            child: Text(
                              adv.name.isNotEmpty
                                  ? adv.name[0].toUpperCase()
                                  : 'A',
                              style: const TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                                color: AppColors.navy,
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
                                  color: AppColors.accent,
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
    // Solo la primera carga ocupa toda la pantalla: en las siguientes (al
    // buscar o filtrar) el buscador debe seguir ahí, o se cerraría el teclado.
    if (_loading && _stages.isEmpty) return const LoadingView();
    if (_error != null && _stages.isEmpty) {
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

    final currency = Fmt.money();
    final auth = context.watch<AuthService>();
    final isAdmin = auth.isAdmin;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colors = AppColors.of(context);

    return Scaffold(
      body: Column(
        children: [
          if (isAdmin)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 7),
              decoration: BoxDecoration(
                color: isDark ? AppColors.darkCard : const Color(0xFFF8FAFC),
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
                          color: AppColors.accent.withValues(alpha: 0.35),
                          width: 1.2,
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(
                            Icons.person_search_rounded,
                            size: 15,
                            color: AppColors.accent,
                          ),
                          const SizedBox(width: 6),
                          Text(
                            _currentAdvisorLabel,
                            style: const TextStyle(
                              fontSize: 12.5,
                              fontWeight: FontWeight.w800,
                              color: AppColors.navy,
                            ),
                          ),
                          const SizedBox(width: 4),
                          const Icon(
                            Icons.arrow_drop_down_rounded,
                            size: 18,
                            color: AppColors.accent,
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
                      color: AppColors.navy.withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      '$_totalLeadsCount ${_totalLeadsCount == 1 ? 'lead' : 'leads'}',
                      style: const TextStyle(
                        fontSize: 11.5,
                        fontWeight: FontWeight.w800,
                        color: AppColors.navy,
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
                color: isDark ? AppColors.darkCard : const Color(0xFFF8FAFC),
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
                    color: AppColors.accent,
                  ),
                  const SizedBox(width: 6),
                  const Text(
                    'Mis Oportunidades Asignadas',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: AppColors.navy,
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

          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 6),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _searchCtrl,
                    onChanged: _onSearchChanged,
                    textInputAction: TextInputAction.search,
                    decoration: InputDecoration(
                      isDense: true,
                      hintText: 'Buscar lead, cliente, asesor o teléfono…',
                      prefixIcon: const Icon(Icons.search_rounded, size: 20),
                      suffixIcon: _searchCtrl.text.isEmpty
                          ? null
                          : IconButton(
                              tooltip: 'Limpiar búsqueda',
                              icon: const Icon(Icons.close_rounded, size: 18),
                              onPressed: _clearSearch,
                            ),
                      contentPadding: const EdgeInsets.symmetric(vertical: 10),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                AddSquareButton(
                  onTap: _openCreate,
                  tooltip: 'Nuevo lead',
                  icon: Icons.person_add_alt_1_rounded,
                ),
              ],
            ),
          ),
          SizedBox(
            height: 2,
            child: _loading ? const LinearProgressIndicator() : null,
          ),

          if (_query.isNotEmpty && !_loading && _totalLeadsCount == 0)
            Expanded(
              child: MessageView(
                icon: Icons.search_off_rounded,
                message: 'Ningún lead coincide con "$_query".',
              ),
            )
          else
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
                    totalCount: _countByStage[stage.id] ?? leads.length,
                    loadingMore: _loadingMore.contains(stage.id),
                    onLoadMore: () => _loadMore(stage.id),
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
  final int totalCount;
  final bool loadingMore;
  final VoidCallback onLoadMore;
  final NumberFormat currency;
  final VoidCallback onRefresh;

  const _StageColumn({
    required this.stage,
    required this.leads,
    required this.totalCount,
    required this.loadingMore,
    required this.onLoadMore,
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
                    '$totalCount',
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
                : NotificationListener<ScrollNotification>(
                    // Al acercarse al final se piden los siguientes leads.
                    onNotification: (n) {
                      if (n.metrics.axis == Axis.vertical &&
                          n.metrics.extentAfter < 400 &&
                          leads.length < totalCount) {
                        onLoadMore();
                      }
                      return false;
                    },
                    child: ListView.separated(
                      physics: const AlwaysScrollableScrollPhysics(),
                      padding: const EdgeInsets.fromLTRB(10, 0, 10, 100),
                      itemCount:
                          leads.length + (leads.length < totalCount ? 1 : 0),
                      separatorBuilder: (_, _) => const SizedBox(height: 8),
                      itemBuilder: (context, i) {
                        if (i >= leads.length) {
                          return Padding(
                            padding: const EdgeInsets.symmetric(vertical: 14),
                            child: Center(
                              child: loadingMore
                                  ? const SizedBox(
                                      width: 22,
                                      height: 22,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2.4,
                                      ),
                                    )
                                  : TextButton(
                                      onPressed: onLoadMore,
                                      child: Text(
                                        'Ver más (${totalCount - leads.length})',
                                      ),
                                    ),
                            ),
                          );
                        }
                        return _FunnelCard(
                          lead: leads[i],
                          currency: currency,
                          onRefresh: onRefresh,
                        );
                      },
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
                  const SizedBox(width: 2),
                  SizedBox(
                    width: 30,
                    height: 30,
                    child: IconButton(
                      padding: EdgeInsets.zero,
                      iconSize: 18,
                      tooltip: 'Nuevo recordatorio',
                      icon: Icon(
                        Icons.notification_add_outlined,
                        color: colors.muted,
                      ),
                      onPressed: () => openNewReminderForLead(context, lead),
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
                      Fmt.phone(lead.phone),
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
              if (lead.createDate != null) ...[
                const SizedBox(height: 3),
                Row(
                  children: [
                    Icon(
                      Icons.event_note_outlined,
                      size: 13,
                      color: colors.mutedLight,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      'Creado el ${DateFormat('d MMM y', 'es_EC').format(lead.createDate!)}',
                      style: TextStyle(fontSize: 12, color: colors.muted),
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
