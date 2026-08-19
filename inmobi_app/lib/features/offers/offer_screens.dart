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
import 'offer_model.dart';
import 'offer_service.dart';

/// Lista de ofertas — general, o acotada a una propiedad / lead concreto.
class OfferListScreen extends StatefulWidget {
  final int? propertyId;
  final String? propertyName;
  final int? leadId;
  final String? title;

  const OfferListScreen({
    super.key,
    this.propertyId,
    this.propertyName,
    this.leadId,
    this.title,
  });

  @override
  State<OfferListScreen> createState() => _OfferListScreenState();
}

class _OfferListScreenState extends State<OfferListScreen> {
  late final OdooClient _odoo;
  late final OfferService _service;
  int _version = 0;

  static const _filters = [
    (null, 'Todas'),
    ('draft', 'Borrador'),
    ('submitted', 'Presentadas'),
    ('countered', 'Contraoferta'),
    ('accepted', 'Aceptadas'),
    ('rejected', 'Rechazadas'),
  ];

  @override
  void initState() {
    super.initState();
    _odoo = context.read<AuthService>().odoo;
    _service = OfferService(_odoo);
  }

  Future<void> _openForm({Offer? existing}) async {
    final saved = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => OfferFormScreen(
          existing: existing,
          initialPropertyId: widget.propertyId,
          initialPropertyName: widget.propertyName,
          initialLeadId: widget.leadId,
        ),
      ),
    );
    if (saved == true) setState(() => _version++);
  }

  @override
  Widget build(BuildContext context) {
    final currency = NumberFormat.currency(
      locale: 'es_EC',
      symbol: '\$',
      decimalDigits: 0,
    );
    return RecordListScaffold<Offer>(
      key: ValueKey(_version),
      title: widget.title ?? 'Ofertas',
      filters: _filters,
      errorMessage: 'No se pudieron cargar las ofertas.',
      emptyMessage: 'No hay ofertas registradas.',
      emptyIcon: Icons.handshake_outlined,
      onCreate: () => _openForm(),
      createLabel: 'Oferta',
      load: (filter) => _service.list(
        state: filter,
        propertyId: widget.propertyId,
        leadId: widget.leadId,
      ),
      summaryBuilder: (items) {
        if (items.isEmpty) return null;
        final accepted = items.where((o) => o.state == 'accepted').length;
        final best = items.fold<double>(
          0,
          (m, o) => o.offerAmount > m ? o.offerAmount : m,
        );
        return TotalsBar(
          entries: [
            ('Ofertas', '${items.length}'),
            ('Aceptadas', '$accepted'),
            ('Mejor oferta', best > 0 ? currency.format(best) : '—'),
          ],
        );
      },
      itemBuilder: (context, offer) => _OfferCard(
        offer: offer,
        currency: currency,
        service: _service,
        onChanged: () => setState(() => _version++),
        onEdit: () => _openForm(existing: offer),
      ),
    );
  }
}

class _OfferCard extends StatelessWidget {
  final Offer offer;
  final NumberFormat currency;
  final OfferService service;
  final VoidCallback onChanged;
  final VoidCallback onEdit;

  const _OfferCard({
    required this.offer,
    required this.currency,
    required this.service,
    required this.onChanged,
    required this.onEdit,
  });

  Future<void> _run(
    BuildContext context,
    String method,
    String successMsg,
  ) async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      await service.runAction(offer.id, method);
      messenger.showSnackBar(SnackBar(content: Text(successMsg)));
      onChanged();
    } catch (e) {
      messenger.showSnackBar(
        const SnackBar(
          content: Text(
            'Odoo rechazó la acción. Revisa el estado de la oferta.',
          ),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = AppColors.of(context);
    final dateFmt = DateFormat('d MMM y', 'es_EC');

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
                    offer.reference.isEmpty
                        ? 'Oferta #${offer.id}'
                        : offer.reference,
                    style: AppType.heading.copyWith(color: p.ink),
                  ),
                ),
                AppBadge(
                  label: OfferStateStyle.label(offer.state),
                  color: OfferStateStyle.color(offer.state),
                ),
              ],
            ),
            if (offer.propertyName.isNotEmpty) ...[
              const SizedBox(height: 3),
              Text(
                offer.propertyName,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: AppType.bodySmall.copyWith(color: p.muted),
              ),
            ],
            if (offer.partnerName.isNotEmpty) ...[
              const SizedBox(height: 2),
              Row(
                children: [
                  Icon(Icons.person_outline, size: 13, color: p.mutedLight),
                  const SizedBox(width: 4),
                  Expanded(
                    child: Text(
                      offer.partnerName,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: AppType.caption.copyWith(color: p.muted),
                    ),
                  ),
                ],
              ),
            ],
            const SizedBox(height: AppSpace.md),
            // Comparativa pedido / ofertado — el dato que importa de un vistazo.
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpace.md,
                vertical: AppSpace.sm,
              ),
              decoration: BoxDecoration(
                color: p.surfaceAlt,
                borderRadius: BorderRadius.circular(AppRadius.sm),
              ),
              child: Row(
                children: [
                  _AmountCell(
                    label: 'Pedido',
                    value: currency.format(offer.askingPrice),
                    muted: true,
                  ),
                  Container(width: 1, height: 26, color: p.line),
                  _AmountCell(
                    label: 'Ofertado',
                    value: currency.format(offer.offerAmount),
                    highlight: true,
                  ),
                  if (offer.counterofferAmount > 0) ...[
                    Container(width: 1, height: 26, color: p.line),
                    _AmountCell(
                      label: 'Contra',
                      value: currency.format(offer.counterofferAmount),
                    ),
                  ],
                  if (offer.finalAgreedAmount > 0) ...[
                    Container(width: 1, height: 26, color: p.line),
                    _AmountCell(
                      label: 'Final',
                      value: currency.format(offer.finalAgreedAmount),
                      color: p.success,
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: AppSpace.sm),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                if (offer.discountPct != 0)
                  AppBadge(
                    label: '${offer.discountPct.toStringAsFixed(1)}% desc.',
                    color: offer.discountPct > 10
                        ? AppColors.danger
                        : AppColors.warning,
                  ),
                AppBadge(
                  label: OfferFinancingStyle.label(offer.financingType),
                  color: AppColors.mutedLight,
                ),
                if (offer.date != null)
                  AppBadge(
                    label: dateFmt.format(offer.date!),
                    color: AppColors.mutedLight,
                  ),
              ],
            ),
            const SizedBox(height: AppSpace.md),
            // Acciones del flujo: se ofrecen solo las válidas para el estado.
            Row(
              children: [
                if (offer.state == 'draft')
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () =>
                          _run(context, 'action_submit', 'Oferta presentada.'),
                      child: const Text('Presentar'),
                    ),
                  ),
                if (offer.state == 'submitted' ||
                    offer.state == 'countered') ...[
                  Expanded(
                    child: FilledButton(
                      onPressed: () =>
                          _run(context, 'action_accept', 'Oferta aceptada.'),
                      style: FilledButton.styleFrom(backgroundColor: p.success),
                      child: const Text('Aceptar'),
                    ),
                  ),
                  const SizedBox(width: AppSpace.sm),
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () =>
                          _run(context, 'action_reject', 'Oferta rechazada.'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: p.danger,
                        side: BorderSide(color: p.danger),
                      ),
                      child: const Text('Rechazar'),
                    ),
                  ),
                ],
                if (offer.state == 'accepted')
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => _run(
                        context,
                        'action_create_contract',
                        'Contrato creado desde la oferta.',
                      ),
                      icon: const Icon(Icons.description_outlined, size: 17),
                      label: const Text('Crear contrato'),
                    ),
                  ),
                const SizedBox(width: AppSpace.sm),
                IconButton(
                  onPressed: onEdit,
                  icon: const Icon(Icons.edit_outlined, size: 19),
                  tooltip: 'Editar oferta',
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _AmountCell extends StatelessWidget {
  final String label;
  final String value;
  final bool muted;
  final bool highlight;
  final Color? color;

  const _AmountCell({
    required this.label,
    required this.value,
    this.muted = false,
    this.highlight = false,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final p = AppColors.of(context);
    return Expanded(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 6),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: AppType.caption.copyWith(
                color: p.mutedLight,
                fontSize: 10,
              ),
            ),
            const SizedBox(height: 1),
            Text(
              value,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 13,
                fontWeight: highlight ? FontWeight.w600 : FontWeight.w400,
                color: color ?? (muted ? p.muted : p.ink),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Alta y edición de una oferta.
class OfferFormScreen extends StatefulWidget {
  final Offer? existing;
  final int? initialPropertyId;
  final String? initialPropertyName;
  final int? initialLeadId;

  const OfferFormScreen({
    super.key,
    this.existing,
    this.initialPropertyId,
    this.initialPropertyName,
    this.initialLeadId,
  });

  bool get isEdit => existing != null;

  @override
  State<OfferFormScreen> createState() => _OfferFormScreenState();
}

class _OfferFormScreenState extends State<OfferFormScreen> {
  final _formKey = GlobalKey<FormState>();
  late final OdooClient _odoo;
  late final OfferService _service;

  final _amountCtrl = TextEditingController();
  final _counterCtrl = TextEditingController();
  final _finalCtrl = TextEditingController();
  final _notesCtrl = TextEditingController();
  Many2oneValue? _property;
  Many2oneValue? _partner;
  String _financing = 'cash';
  DateTime _date = DateTime.now();
  DateTime? _expiry;

  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _odoo = context.read<AuthService>().odoo;
    _service = OfferService(_odoo);
    final o = widget.existing;
    if (o != null) {
      _amountCtrl.text = o.offerAmount > 0
          ? o.offerAmount.toStringAsFixed(0)
          : '';
      _counterCtrl.text = o.counterofferAmount > 0
          ? o.counterofferAmount.toStringAsFixed(0)
          : '';
      _finalCtrl.text = o.finalAgreedAmount > 0
          ? o.finalAgreedAmount.toStringAsFixed(0)
          : '';
      _notesCtrl.text = o.notes;
      _financing = o.financingType;
      _date = o.date ?? DateTime.now();
      _expiry = o.dateExpiry;
      if (o.propertyId != null)
        _property = Many2oneValue(o.propertyId!, o.propertyName);
      if (o.partnerId != null)
        _partner = Many2oneValue(o.partnerId!, o.partnerName);
    } else if (widget.initialPropertyId != null) {
      _property = Many2oneValue(
        widget.initialPropertyId!,
        widget.initialPropertyName ?? '',
      );
    }
  }

  @override
  void dispose() {
    _amountCtrl.dispose();
    _counterCtrl.dispose();
    _finalCtrl.dispose();
    _notesCtrl.dispose();
    super.dispose();
  }

  String _fmt(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  Future<void> _pickDate({required bool isExpiry}) async {
    final picked = await showDatePicker(
      context: context,
      initialDate: isExpiry ? (_expiry ?? DateTime.now()) : _date,
      firstDate: DateTime(2015),
      lastDate: DateTime(2100),
    );
    if (picked == null) return;
    setState(() => isExpiry ? _expiry = picked : _date = picked);
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    if (_property == null || _partner == null) {
      setState(() => _error = 'Selecciona la propiedad y el interesado.');
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });

    final vals = {
      'property_id': _property!.id,
      'partner_id': _partner!.id,
      if (widget.initialLeadId != null) 'lead_id': widget.initialLeadId,
      'offer_amount': double.tryParse(_amountCtrl.text.trim()) ?? 0.0,
      'counteroffer_amount': double.tryParse(_counterCtrl.text.trim()) ?? 0.0,
      'final_agreed_amount': double.tryParse(_finalCtrl.text.trim()) ?? 0.0,
      'financing_type': _financing,
      'date': _fmt(_date),
      if (_expiry != null) 'date_expiry': _fmt(_expiry!),
      'notes': _notesCtrl.text.trim(),
    };

    try {
      if (widget.isEdit) {
        await _service.update(widget.existing!.id, vals);
      } else {
        await _service.create(vals);
      }
      if (mounted) Navigator.of(context).pop(true);
    } catch (e) {
      if (mounted)
        setState(
          () => _error = 'No se pudo guardar la oferta. Intenta de nuevo.',
        );
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = AppColors.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.isEdit ? 'Editar oferta' : 'Nueva oferta'),
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(AppSpace.lg),
          children: [
            Many2oneField(
              label: 'Propiedad',
              required: true,
              odoo: _odoo,
              model: 'estate.property',
              searchField: 'title',
              value: _property,
              onChanged: (v) => setState(() => _property = v),
            ),
            const SizedBox(height: AppSpace.md),
            Many2oneField(
              label: 'Interesado / Comprador',
              required: true,
              odoo: _odoo,
              model: 'res.partner',
              value: _partner,
              onChanged: (v) => setState(() => _partner = v),
            ),
            const SizedBox(height: AppSpace.md),
            TextFormField(
              controller: _amountCtrl,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Monto ofertado (\$) *',
              ),
              validator: (v) {
                final n = double.tryParse((v ?? '').trim());
                return (n == null || n <= 0) ? 'Ingresa un monto válido' : null;
              },
            ),
            const SizedBox(height: AppSpace.md),
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: _counterCtrl,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Contraoferta (\$)',
                    ),
                  ),
                ),
                const SizedBox(width: AppSpace.md),
                Expanded(
                  child: TextFormField(
                    controller: _finalCtrl,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Precio final (\$)',
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpace.md),
            SelectField(
              label: 'Tipo de financiamiento',
              value: _financing,
              options: OfferFinancingStyle.options,
              onChanged: (v) => setState(() => _financing = v ?? 'cash'),
            ),
            const SizedBox(height: AppSpace.md),
            Row(
              children: [
                Expanded(
                  child: InkWell(
                    borderRadius: BorderRadius.circular(AppRadius.md),
                    onTap: () => _pickDate(isExpiry: false),
                    child: InputDecorator(
                      decoration: const InputDecoration(
                        labelText: 'Fecha de oferta',
                      ),
                      child: Text(_fmt(_date)),
                    ),
                  ),
                ),
                const SizedBox(width: AppSpace.md),
                Expanded(
                  child: InkWell(
                    borderRadius: BorderRadius.circular(AppRadius.md),
                    onTap: () => _pickDate(isExpiry: true),
                    child: InputDecorator(
                      decoration: InputDecoration(
                        labelText: 'Válida hasta',
                        suffixIcon: _expiry != null
                            ? IconButton(
                                icon: const Icon(Icons.close, size: 18),
                                onPressed: () => setState(() => _expiry = null),
                              )
                            : null,
                      ),
                      child: Text(
                        _expiry != null ? _fmt(_expiry!) : 'Sin definir',
                        style: TextStyle(
                          color: _expiry != null ? p.ink : p.mutedLight,
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpace.md),
            TextFormField(
              controller: _notesCtrl,
              minLines: 3,
              maxLines: 6,
              decoration: const InputDecoration(
                labelText: 'Observaciones',
                alignLabelWithHint: true,
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: AppSpace.md),
              Text(_error!, style: TextStyle(color: p.danger)),
            ],
            const SizedBox(height: AppSpace.xl),
            ElevatedButton(
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
                  : Text(widget.isEdit ? 'Guardar cambios' : 'Crear oferta'),
            ),
          ],
        ),
      ),
    );
  }
}
