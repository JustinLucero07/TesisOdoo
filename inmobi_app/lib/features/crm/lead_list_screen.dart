import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/app_badge.dart';
import '../../core/widgets/states.dart';
import '../../core/widgets/skeleton.dart';
import '../auth/auth_service.dart';
import 'crm_stage_service.dart';
import 'lead_detail_screen.dart';
import 'lead_form_screen.dart';
import 'lead_model.dart';
import 'lead_service.dart';

class LeadListScreen extends StatefulWidget {
  const LeadListScreen({super.key});

  @override
  State<LeadListScreen> createState() => _LeadListScreenState();
}

class _LeadListScreenState extends State<LeadListScreen> {
  late final LeadService _service;
  late final CrmStageService _stageService;
  final _searchCtrl = TextEditingController();
  String? _temperatureFilter;
  int? _stageFilter;
  List<CrmStage> _stages = [];

  List<Lead> _leads = [];
  bool _loading = true;
  String? _error;

  static const _filters = [
    (null, 'Todos'),
    ('boiling', '¡Hirviendo!'),
    ('hot', 'Caliente'),
    ('warm', 'Tibio'),
    ('cold', 'Frío'),
  ];

  @override
  void initState() {
    super.initState();
    final odoo = context.read<AuthService>().odoo;
    _service = LeadService(odoo);
    _stageService = CrmStageService(odoo);
    _stageService.list().then((s) {
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
      final result = await _service.list(
        searchText: _searchCtrl.text,
        temperature: _temperatureFilter,
        stageId: _stageFilter,
      );
      setState(() => _leads = result);
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

  @override
  Widget build(BuildContext context) {
    final currency = NumberFormat.currency(
      locale: 'es_EC',
      symbol: '\$',
      decimalDigits: 0,
    );
    return Scaffold(
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _openCreate,
        icon: const Icon(Icons.add),
        label: const Text('Lead'),
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
              child: TextField(
                controller: _searchCtrl,
                decoration: InputDecoration(
                  hintText: 'Buscar lead...',
                  prefixIcon: const Icon(Icons.search),
                  suffixIcon: IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () {
                      _searchCtrl.clear();
                      _load();
                    },
                  ),
                ),
                onSubmitted: (_) => _load(),
              ),
            ),
            SizedBox(
              height: 44,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 6,
                ),
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
            if (_stages.isNotEmpty)
              SizedBox(
                height: 40,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 4,
                  ),
                  itemCount: _stages.length + 1,
                  separatorBuilder: (_, _) => const SizedBox(width: 8),
                  itemBuilder: (context, i) {
                    final stageId = i == 0 ? null : _stages[i - 1].id;
                    final label = i == 0
                        ? 'Todas las etapas'
                        : _stages[i - 1].name;
                    final selected = _stageFilter == stageId;
                    return ChoiceChip(
                      label: Text(label),
                      selected: selected,
                      selectedColor: AppColors.navyLight,
                      backgroundColor: AppColors.neutralBg,
                      labelStyle: TextStyle(
                        color: selected ? Colors.white : AppColors.ink,
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
    return ListView.separated(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
      itemCount: _leads.length,
      separatorBuilder: (_, _) => const SizedBox(height: 10),
      itemBuilder: (context, i) {
        final lead = _leads[i];
        return Card(
          child: InkWell(
            borderRadius: BorderRadius.circular(14),
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => LeadDetailScreen(leadId: lead.id),
              ),
            ),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          lead.name,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            fontWeight: FontWeight.w700,
                            fontSize: 15,
                          ),
                        ),
                      ),
                      AppBadge(
                        label: LeadTemperatureStyle.label(lead.leadTemperature),
                        color: LeadTemperatureStyle.color(lead.leadTemperature),
                        icon: LeadTemperatureStyle.icon(lead.leadTemperature),
                      ),
                    ],
                  ),
                  if (lead.contactName.isNotEmpty) ...[
                    const SizedBox(height: 3),
                    Text(
                      lead.contactName,
                      style: const TextStyle(
                        color: AppColors.muted,
                        fontSize: 12.5,
                      ),
                    ),
                  ],
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      AppBadge(
                        label: LeadScoreStyle.label(lead.leadScore),
                        color: LeadScoreStyle.color(lead.leadScore),
                      ),
                      const SizedBox(width: 8),
                      if (lead.matchPercentage > 0)
                        Text(
                          '${lead.matchPercentage}% match',
                          style: const TextStyle(
                            fontSize: 12,
                            color: AppColors.mutedLight,
                          ),
                        ),
                      const Spacer(),
                      if (lead.clientBudget > 0)
                        Text(
                          currency.format(lead.clientBudget),
                          style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            color: AppColors.navy,
                            fontSize: 13.5,
                          ),
                        ),
                    ],
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
