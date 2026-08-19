import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../core/api/odoo_client.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/app_badge.dart';
import '../../core/widgets/many2one_field.dart';
import '../../core/widgets/record_list_scaffold.dart';
import '../../core/widgets/select_field.dart';
import '../auth/auth_service.dart';
import 'finance_models.dart';

NumberFormat get _currency =>
    NumberFormat.currency(locale: 'es_EC', symbol: '\$', decimalDigits: 0);
DateFormat get _dateFmt => DateFormat('d MMM y', 'es_EC');

/// ───────────────────────── Comisiones ─────────────────────────
class CommissionListScreen extends StatelessWidget {
  final bool onlyMine;
  const CommissionListScreen({super.key, this.onlyMine = true});

  @override
  Widget build(BuildContext context) {
    final odoo = context.read<AuthService>().odoo;
    return RecordListScaffold<Commission>(
      title: onlyMine ? 'Mis comisiones' : 'Comisiones',
      errorMessage: 'No se pudieron cargar las comisiones.',
      emptyMessage: 'No hay comisiones registradas.',
      emptyIcon: Icons.payments_outlined,
      filters: const [
        (null, 'Todas'),
        ('draft', 'Borrador'),
        ('approved', 'Aprobadas'),
        ('paid', 'Pagadas'),
      ],
      load: (filter) async {
        final domain = <dynamic>[];
        if (filter != null) domain.add(['state', '=', filter]);
        if (onlyMine && odoo.uid != null)
          domain.add(['user_id', '=', odoo.uid]);
        final rows = await odoo.searchRead(
          model: 'estate.commission',
          domain: domain,
          fields: Commission.fields,
          order: 'date desc, id desc',
          limit: 120,
        );
        return rows.map(Commission.fromJson).toList();
      },
      summaryBuilder: (items) {
        if (items.isEmpty) return null;
        final paid = items
            .where((c) => c.state == 'paid')
            .fold<double>(0, (s, c) => s + c.amount);
        final pending = items
            .where((c) => c.state == 'approved' || c.state == 'draft')
            .fold<double>(0, (s, c) => s + c.amount);
        return TotalsBar(
          entries: [
            ('Cobrado', _currency.format(paid)),
            ('Por cobrar', _currency.format(pending)),
            ('Registros', '${items.length}'),
          ],
        );
      },
      itemBuilder: (context, c) {
        final p = AppColors.of(context);
        return Card(
          child: Padding(
            padding: const EdgeInsets.all(AppSpace.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        c.propertyName.isNotEmpty
                            ? c.propertyName
                            : c.reference,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: AppType.heading.copyWith(color: p.ink),
                      ),
                    ),
                    AppBadge(
                      label: Commission.stateLabel(c.state),
                      color: Commission.stateColor(c.state),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpace.sm),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Comisión ${c.commissionPct.toStringAsFixed(1)}%',
                            style: AppType.caption.copyWith(
                              color: p.mutedLight,
                            ),
                          ),
                          const SizedBox(height: 1),
                          Text(
                            _currency.format(c.amount),
                            style: AppType.numeric.copyWith(
                              fontSize: 20,
                              color: p.navy,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text(
                          'Sobre ${_currency.format(c.saleAmount)}',
                          style: AppType.caption.copyWith(color: p.mutedLight),
                        ),
                        if (c.date != null)
                          Text(
                            _dateFmt.format(c.date!),
                            style: AppType.caption.copyWith(color: p.muted),
                          ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: AppSpace.sm),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    AppBadge(
                      label: Commission.typeLabel(c.type),
                      color: AppColors.mutedLight,
                    ),
                    if (!onlyMine && c.userName.isNotEmpty)
                      AppBadge(label: c.userName, color: AppColors.navyLight),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

/// ───────────────────────── Pagos ─────────────────────────
class PaymentListScreen extends StatelessWidget {
  final int? propertyId;
  final int? contractId;
  const PaymentListScreen({super.key, this.propertyId, this.contractId});

  @override
  Widget build(BuildContext context) {
    final odoo = context.read<AuthService>().odoo;
    return RecordListScaffold<Payment>(
      title: 'Pagos',
      errorMessage: 'No se pudieron cargar los pagos.',
      emptyMessage: 'No hay pagos registrados.',
      emptyIcon: Icons.receipt_long_outlined,
      filters: const [
        (null, 'Todos'),
        ('pending', 'Pendientes'),
        ('paid', 'Pagados'),
        ('cancelled', 'Anulados'),
      ],
      load: (filter) async {
        final domain = <dynamic>[];
        if (filter != null) domain.add(['state', '=', filter]);
        if (propertyId != null) domain.add(['property_id', '=', propertyId]);
        if (contractId != null) domain.add(['contract_id', '=', contractId]);
        final rows = await odoo.searchRead(
          model: 'estate.payment',
          domain: domain,
          fields: Payment.fields,
          order: 'date desc, id desc',
          limit: 120,
        );
        return rows.map(Payment.fromJson).toList();
      },
      summaryBuilder: (items) {
        if (items.isEmpty) return null;
        final paid = items
            .where((x) => x.state == 'paid')
            .fold<double>(0, (s, x) => s + x.amount);
        final pending = items
            .where((x) => x.state == 'pending')
            .fold<double>(0, (s, x) => s + x.amount);
        return TotalsBar(
          entries: [
            ('Cobrado', _currency.format(paid)),
            ('Pendiente', _currency.format(pending)),
          ],
        );
      },
      itemBuilder: (context, pay) {
        final p = AppColors.of(context);
        return Card(
          child: Padding(
            padding: const EdgeInsets.all(AppSpace.lg),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        pay.reference.isEmpty
                            ? 'Pago #${pay.id}'
                            : pay.reference,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: AppType.body.copyWith(
                          fontWeight: FontWeight.w600,
                          color: p.ink,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        [
                          if (pay.partnerName.isNotEmpty) pay.partnerName,
                          if (pay.propertyName.isNotEmpty) pay.propertyName,
                        ].join(' · '),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: AppType.caption.copyWith(color: p.muted),
                      ),
                      const SizedBox(height: AppSpace.sm),
                      Wrap(
                        spacing: 6,
                        children: [
                          AppBadge(
                            label: Payment.stateLabel(pay.state),
                            color: Payment.stateColor(pay.state),
                          ),
                          AppBadge(
                            label: Payment.methodLabel(pay.method),
                            color: AppColors.mutedLight,
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: AppSpace.md),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      _currency.format(pay.amount),
                      style: AppType.heading.copyWith(color: p.navy),
                    ),
                    if (pay.date != null)
                      Text(
                        _dateFmt.format(pay.date!),
                        style: AppType.caption.copyWith(color: p.mutedLight),
                      ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

/// ───────────────────────── Gastos ─────────────────────────
class ExpenseListScreen extends StatefulWidget {
  final int? propertyId;
  final String? propertyName;
  const ExpenseListScreen({super.key, this.propertyId, this.propertyName});

  @override
  State<ExpenseListScreen> createState() => _ExpenseListScreenState();
}

class _ExpenseListScreenState extends State<ExpenseListScreen> {
  int _version = 0;

  static const _typeOptions = [
    ('maintenance', 'Mantenimiento'),
    ('repair', 'Reparación'),
    ('marketing', 'Marketing'),
    ('legal', 'Legal'),
    ('tax', 'Impuestos'),
    ('other', 'Otro'),
  ];

  Future<void> _create() async {
    final odoo = context.read<AuthService>().odoo;
    final saved = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _ExpenseSheet(
        odoo: odoo,
        initialPropertyId: widget.propertyId,
        initialPropertyName: widget.propertyName,
        typeOptions: _typeOptions,
      ),
    );
    if (saved == true) setState(() => _version++);
  }

  @override
  Widget build(BuildContext context) {
    final odoo = context.read<AuthService>().odoo;
    return RecordListScaffold<Expense>(
      key: ValueKey(_version),
      title: 'Gastos',
      errorMessage: 'No se pudieron cargar los gastos.',
      emptyMessage: 'No hay gastos registrados.',
      emptyIcon: Icons.request_quote_outlined,
      onCreate: _create,
      createLabel: 'Gasto',
      load: (_) async {
        final domain = <dynamic>[];
        if (widget.propertyId != null)
          domain.add(['property_id', '=', widget.propertyId]);
        final rows = await odoo.searchRead(
          model: 'estate.property.expense',
          domain: domain,
          fields: Expense.fields,
          order: 'date desc, id desc',
          limit: 120,
        );
        return rows.map(Expense.fromJson).toList();
      },
      summaryBuilder: (items) {
        if (items.isEmpty) return null;
        final total = items.fold<double>(0, (s, e) => s + e.amount);
        final pendingReimb = items
            .where((e) => e.reimbursable && !e.reimbursed)
            .fold<double>(0, (s, e) => s + e.amount);
        return TotalsBar(
          entries: [
            ('Total gastado', _currency.format(total)),
            ('Por reembolsar', _currency.format(pendingReimb)),
          ],
        );
      },
      itemBuilder: (context, e) {
        final p = AppColors.of(context);
        final typeLabel = _typeOptions
            .firstWhere(
              (t) => t.$1 == e.expenseType,
              orElse: () => ('other', 'Otro'),
            )
            .$2;
        return Card(
          child: Padding(
            padding: const EdgeInsets.all(AppSpace.lg),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        e.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: AppType.body.copyWith(
                          fontWeight: FontWeight.w600,
                          color: p.ink,
                        ),
                      ),
                      if (e.propertyName.isNotEmpty) ...[
                        const SizedBox(height: 2),
                        Text(
                          e.propertyName,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: AppType.caption.copyWith(color: p.muted),
                        ),
                      ],
                      const SizedBox(height: AppSpace.sm),
                      Wrap(
                        spacing: 6,
                        runSpacing: 6,
                        children: [
                          AppBadge(
                            label: typeLabel,
                            color: AppColors.mutedLight,
                          ),
                          if (e.reimbursable)
                            AppBadge(
                              label: e.reimbursed
                                  ? 'Reembolsado'
                                  : 'Por reembolsar',
                              color: e.reimbursed
                                  ? AppColors.success
                                  : AppColors.warning,
                            ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: AppSpace.md),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      _currency.format(e.amount),
                      style: AppType.heading.copyWith(color: p.ink),
                    ),
                    if (e.date != null)
                      Text(
                        _dateFmt.format(e.date!),
                        style: AppType.caption.copyWith(color: p.mutedLight),
                      ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _ExpenseSheet extends StatefulWidget {
  final OdooClient odoo;
  final int? initialPropertyId;
  final String? initialPropertyName;
  final List<(String, String)> typeOptions;

  const _ExpenseSheet({
    required this.odoo,
    required this.typeOptions,
    this.initialPropertyId,
    this.initialPropertyName,
  });

  @override
  State<_ExpenseSheet> createState() => _ExpenseSheetState();
}

class _ExpenseSheetState extends State<_ExpenseSheet> {
  final _nameCtrl = TextEditingController();
  final _amountCtrl = TextEditingController();
  Many2oneValue? _property;
  String _type = 'maintenance';
  bool _reimbursable = false;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    if (widget.initialPropertyId != null) {
      _property = Many2oneValue(
        widget.initialPropertyId!,
        widget.initialPropertyName ?? '',
      );
    }
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _amountCtrl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final name = _nameCtrl.text.trim();
    final amount = double.tryParse(_amountCtrl.text.trim()) ?? 0;
    if (name.isEmpty || amount <= 0 || _property == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Completa descripción, propiedad y monto.'),
        ),
      );
      return;
    }
    setState(() => _saving = true);
    try {
      await widget.odoo.create(
        model: 'estate.property.expense',
        values: {
          'name': name,
          'property_id': _property!.id,
          'expense_type': _type,
          'amount': amount,
          'reimbursable': _reimbursable,
        },
      );
      if (mounted) Navigator.of(context).pop(true);
    } catch (e) {
      if (mounted) {
        setState(() => _saving = false);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No se pudo registrar el gasto.')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(
        AppSpace.xl,
        AppSpace.lg,
        AppSpace.xl,
        MediaQuery.of(context).viewInsets.bottom + AppSpace.xl,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Nuevo gasto', style: AppType.title),
          const SizedBox(height: AppSpace.lg),
          TextField(
            controller: _nameCtrl,
            decoration: const InputDecoration(labelText: 'Descripción'),
          ),
          const SizedBox(height: AppSpace.md),
          Many2oneField(
            label: 'Propiedad',
            required: true,
            odoo: widget.odoo,
            model: 'estate.property',
            searchField: 'title',
            value: _property,
            onChanged: (v) => setState(() => _property = v),
          ),
          const SizedBox(height: AppSpace.md),
          Row(
            children: [
              Expanded(
                child: SelectField(
                  label: 'Tipo',
                  value: _type,
                  options: widget.typeOptions,
                  onChanged: (v) => setState(() => _type = v ?? 'other'),
                ),
              ),
              const SizedBox(width: AppSpace.md),
              Expanded(
                child: TextField(
                  controller: _amountCtrl,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'Monto (\$)'),
                ),
              ),
            ],
          ),
          SwitchListTile.adaptive(
            contentPadding: EdgeInsets.zero,
            title: const Text('Reembolsable', style: TextStyle(fontSize: 14)),
            value: _reimbursable,
            onChanged: (v) => setState(() => _reimbursable = v),
          ),
          const SizedBox(height: AppSpace.md),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: _saving ? null : _save,
              child: _saving
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Text('Registrar gasto'),
            ),
          ),
        ],
      ),
    );
  }
}

/// ───────────────────────── Tasaciones ─────────────────────────
class AppraisalListScreen extends StatelessWidget {
  final int? propertyId;
  const AppraisalListScreen({super.key, this.propertyId});

  @override
  Widget build(BuildContext context) {
    final odoo = context.read<AuthService>().odoo;
    return RecordListScaffold<Appraisal>(
      title: 'Tasaciones',
      errorMessage: 'No se pudieron cargar las tasaciones.',
      emptyMessage: 'No hay tasaciones registradas.',
      emptyIcon: Icons.assessment_outlined,
      filters: const [
        (null, 'Todas'),
        ('requested', 'Solicitadas'),
        ('in_progress', 'En proceso'),
        ('completed', 'Completadas'),
      ],
      load: (filter) async {
        final domain = <dynamic>[];
        if (filter != null) domain.add(['state', '=', filter]);
        if (propertyId != null) domain.add(['property_id', '=', propertyId]);
        final rows = await odoo.searchRead(
          model: 'estate.appraisal',
          domain: domain,
          fields: Appraisal.fields,
          order: 'date_requested desc, id desc',
          limit: 80,
        );
        return rows.map(Appraisal.fromJson).toList();
      },
      itemBuilder: (context, a) {
        final p = AppColors.of(context);
        return Card(
          child: Padding(
            padding: const EdgeInsets.all(AppSpace.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        a.propertyName.isNotEmpty
                            ? a.propertyName
                            : a.reference,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: AppType.heading.copyWith(color: p.ink),
                      ),
                    ),
                    AppBadge(
                      label: Appraisal.stateLabel(a.state),
                      color: Appraisal.stateColor(a.state),
                    ),
                  ],
                ),
                if (a.partnerName.isNotEmpty) ...[
                  const SizedBox(height: 2),
                  Text(
                    'Solicita: ${a.partnerName}',
                    style: AppType.caption.copyWith(color: p.muted),
                  ),
                ],
                if (a.marketValue > 0) ...[
                  const SizedBox(height: AppSpace.md),
                  Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Valor tasado',
                              style: AppType.caption.copyWith(
                                color: p.mutedLight,
                              ),
                            ),
                            Text(
                              _currency.format(a.marketValue),
                              style: AppType.heading.copyWith(color: p.navy),
                            ),
                          ],
                        ),
                      ),
                      if (a.variancePct != 0)
                        AppBadge(
                          label:
                              '${a.variancePct > 0 ? '+' : ''}${a.variancePct.toStringAsFixed(1)}% vs precio',
                          color: a.variancePct >= 0
                              ? AppColors.success
                              : AppColors.warning,
                        ),
                    ],
                  ),
                ],
              ],
            ),
          ),
        );
      },
    );
  }
}
