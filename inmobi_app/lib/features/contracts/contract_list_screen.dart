import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/app_badge.dart';
import '../../core/widgets/choice_chip_row.dart';
import '../../core/widgets/skeleton.dart';
import '../../core/widgets/states.dart';
import '../auth/auth_service.dart';
import 'contract_detail_screen.dart';
import 'contract_form_screen.dart';
import 'contract_model.dart';
import 'contract_service.dart';

/// Lista de contratos — si [propertyId] viene seteado, se abre ya filtrada
/// a una sola propiedad (uso desde el "smart button" del detalle de
/// propiedad); si no, muestra todos.
class ContractListScreen extends StatefulWidget {
  final int? propertyId;
  final String? propertyTitle;
  const ContractListScreen({super.key, this.propertyId, this.propertyTitle});

  @override
  State<ContractListScreen> createState() => _ContractListScreenState();
}

class _ContractListScreenState extends State<ContractListScreen> {
  late final ContractService _service;
  final _searchCtrl = TextEditingController();
  String? _stateFilter;
  List<Contract> _contracts = [];
  bool _loading = true;
  String? _error;

  static const _stateFilters = [
    (null, 'Todos'),
    ('draft', 'Borrador'),
    ('active', 'Activo'),
    ('suspended', 'Suspendido'),
    ('renewing', 'En renovación'),
    ('renewed', 'Renovado'),
    ('expired', 'Vencido'),
    ('cancelled', 'Cancelado'),
  ];

  @override
  void initState() {
    super.initState();
    _service = ContractService(context.read<AuthService>().odoo);
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
        propertyId: widget.propertyId,
        state: _stateFilter,
      );
      setState(() => _contracts = result);
    } catch (e) {
      setState(() => _error = 'No se pudieron cargar los contratos.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _openCreate() async {
    final saved = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => ContractFormScreen(
          initialPropertyId: widget.propertyId,
          initialPropertyName: widget.propertyTitle,
        ),
      ),
    );
    if (saved == true) _load();
  }

  @override
  Widget build(BuildContext context) {
    final currency = NumberFormat.currency(
      locale: 'es_EC',
      symbol: '\$',
      decimalDigits: 0,
    );
    final colors = AppColors.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(
          widget.propertyTitle != null
              ? 'Contratos · ${widget.propertyTitle}'
              : 'Contratos',
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        heroTag: null,
        onPressed: _openCreate,
        icon: const Icon(Icons.add),
        label: const Text('Contrato'),
      ),
      body: Column(
        children: [
          if (widget.propertyId == null)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
              child: TextField(
                controller: _searchCtrl,
                decoration: InputDecoration(
                  hintText: 'Buscar por referencia...',
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
          ChoiceChipRow(
            options: _stateFilters,
            value: _stateFilter,
            onChanged: (v) {
              setState(() => _stateFilter = v);
              _load();
            },
          ),
          const SizedBox(height: 8),
          Expanded(
            child: RefreshIndicator(
              onRefresh: _load,
              child: _buildBody(currency, colors),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBody(NumberFormat currency, AppPalette colors) {
    if (_loading) return const SkeletonList();
    if (_error != null) {
      return MessageView(
        icon: Icons.error_outline,
        message: _error!,
        onRetry: _load,
      );
    }
    if (_contracts.isEmpty) {
      return const MessageView(
        icon: Icons.description_outlined,
        message: 'No se encontraron contratos.',
      );
    }
    return ListView.separated(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
      itemCount: _contracts.length,
      separatorBuilder: (_, _) => const SizedBox(height: 10),
      itemBuilder: (context, i) {
        final c = _contracts[i];
        return Card(
          child: InkWell(
            borderRadius: BorderRadius.circular(16),
            onTap: () => Navigator.of(context)
                .push(
                  MaterialPageRoute(
                    builder: (_) => ContractDetailScreen(contractId: c.id),
                  ),
                )
                .then((_) => _load()),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          c.reference.isEmpty
                              ? 'Contrato #${c.id}'
                              : c.reference,
                          style: const TextStyle(
                            fontWeight: FontWeight.w700,
                            fontSize: 15,
                          ),
                        ),
                      ),
                      AppBadge(
                        label: ContractStateStyle.label(c.state),
                        color: ContractStateStyle.color(c.state, colors),
                      ),
                    ],
                  ),
                  const SizedBox(height: 3),
                  Text(
                    c.propertyName.isNotEmpty ? c.propertyName : '—',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: colors.muted,
                      fontSize: 12.5,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          ContractTypeStyle.label(c.contractType),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: 12,
                            color: colors.mutedLight,
                          ),
                        ),
                      ),
                      if (c.amount > 0)
                        Text(
                          currency.format(c.amount),
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: colors.navy,
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
