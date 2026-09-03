import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../core/api/odoo_client.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/app_badge.dart';
import '../../core/widgets/states.dart';
import '../auth/auth_service.dart';
import '../documents/document_service.dart';
import '../documents/documents_section.dart';
import 'contract_form_screen.dart';
import 'contract_model.dart';
import 'contract_service.dart';

class ContractDetailScreen extends StatefulWidget {
  final int contractId;
  const ContractDetailScreen({super.key, required this.contractId});

  @override
  State<ContractDetailScreen> createState() => _ContractDetailScreenState();
}

class _ContractDetailScreenState extends State<ContractDetailScreen> {
  late final OdooClient _odoo;
  late final ContractService _service;
  Contract? _contract;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _odoo = context.read<AuthService>().odoo;
    _service = ContractService(_odoo);
    _load();
  }

  Future<void> _load() async {
    try {
      final c = await _service.detail(widget.contractId);
      setState(() => _contract = c);
    } catch (e) {
      setState(() => _error = 'No se pudo cargar el contrato.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _openEdit() async {
    final saved = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => ContractFormScreen(existing: _contract),
      ),
    );
    if (saved == true) _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Contrato'),
        actions: [
          if (_contract != null)
            IconButton(
              icon: const Icon(Icons.edit_outlined),
              onPressed: _openEdit,
            ),
        ],
      ),
      body: _loading
          ? const LoadingView()
          : _error != null
          ? MessageView(
              icon: Icons.error_outline,
              message: _error!,
              onRetry: _load,
            )
          : _buildBody(AppColors.of(context)),
    );
  }

  Widget _buildBody(AppPalette colors) {
    final c = _contract!;
    final currency = NumberFormat.currency(
      locale: 'es_EC',
      symbol: '\$',
      decimalDigits: 0,
    );
    final dateFmt = DateFormat('d MMM yyyy', 'es_EC');

    return ListView(
      padding: const EdgeInsets.all(18),
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Text(
                c.reference.isEmpty ? 'Contrato #${c.id}' : c.reference,
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            AppBadge(
              label: ContractStateStyle.label(c.state),
              color: ContractStateStyle.color(c.state, colors),
            ),
          ],
        ),
        const SizedBox(height: 6),
        Text(
          ContractTypeStyle.label(c.contractType),
          style: TextStyle(color: colors.muted, fontSize: 13.5),
        ),
        const SizedBox(height: 18),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _InfoRow(
                  icon: Icons.home_work_outlined,
                  label: 'Propiedad',
                  value: c.propertyName.isEmpty ? '—' : c.propertyName,
                ),
                const Divider(height: 22),
                _InfoRow(
                  icon: Icons.person_outline,
                  label: 'Cliente',
                  value: c.partnerName.isEmpty ? '—' : c.partnerName,
                ),
                const Divider(height: 22),
                _InfoRow(
                  icon: Icons.event_outlined,
                  label: 'Vigencia',
                  value: c.dateStart == null
                      ? '—'
                      : '${dateFmt.format(c.dateStart!)}'
                            '${c.dateEnd != null ? ' – ${dateFmt.format(c.dateEnd!)}' : ''}',
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 14),
        Row(
          children: [
            Expanded(
              child: _StatCard(
                icon: Icons.attach_money,
                label: 'Monto',
                value: c.amount > 0 ? currency.format(c.amount) : '—',
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _StatCard(
                icon: Icons.percent,
                label: 'Comisión',
                value: '${c.commissionPercentage.toStringAsFixed(1)}%',
              ),
            ),
          ],
        ),
        const SizedBox(height: 22),
        DocumentsSection(odoo: _odoo, owner: DocumentOwner.contract(c.id)),
      ],
    );
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  const _InfoRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.of(context);
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 18, color: colors.navy),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: TextStyle(
                  fontSize: 11.5,
                  color: colors.mutedLight,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                value,
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _StatCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  const _StatCard({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, size: 18, color: colors.accent),
            const SizedBox(height: 8),
            Text(
              value,
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: colors.navy,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              label,
              style: TextStyle(
                fontSize: 11.5,
                color: colors.mutedLight,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
