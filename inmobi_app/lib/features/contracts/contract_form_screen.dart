import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api/odoo_client.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/many2one_field.dart';
import '../../core/widgets/select_field.dart';
import '../auth/auth_service.dart';
import 'contract_model.dart';
import 'contract_service.dart';

class ContractFormScreen extends StatefulWidget {
  final Contract? existing;
  final int? initialPropertyId;
  final String? initialPropertyName;

  const ContractFormScreen({
    super.key,
    this.existing,
    this.initialPropertyId,
    this.initialPropertyName,
  });

  bool get isEdit => existing != null;

  @override
  State<ContractFormScreen> createState() => _ContractFormScreenState();
}

class _ContractFormScreenState extends State<ContractFormScreen> {
  final _formKey = GlobalKey<FormState>();
  late final OdooClient _odoo;
  late final ContractService _service;

  final _amountCtrl = TextEditingController();
  final _commissionCtrl = TextEditingController(text: '5.0');
  String _contractType = 'exclusive_owner';
  Many2oneValue? _property;
  Many2oneValue? _partner;
  DateTime _dateStart = DateTime.now();
  DateTime? _dateEnd;

  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _odoo = context.read<AuthService>().odoo;
    _service = ContractService(_odoo);
    final c = widget.existing;
    if (c != null) {
      _amountCtrl.text = c.amount > 0 ? c.amount.toStringAsFixed(0) : '';
      _commissionCtrl.text = c.commissionPercentage.toStringAsFixed(1);
      _contractType = c.contractType;
      if (c.propertyId != null)
        _property = Many2oneValue(c.propertyId!, c.propertyName);
      if (c.partnerId != null)
        _partner = Many2oneValue(c.partnerId!, c.partnerName);
      _dateStart = c.dateStart ?? DateTime.now();
      _dateEnd = c.dateEnd;
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
    _commissionCtrl.dispose();
    super.dispose();
  }

  Future<void> _pickDate({required bool isStart}) async {
    final initial = isStart ? _dateStart : (_dateEnd ?? _dateStart);
    final picked = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(2015),
      lastDate: DateTime(2100),
    );
    if (picked == null) return;
    setState(() {
      if (isStart) {
        _dateStart = picked;
      } else {
        _dateEnd = picked;
      }
    });
  }

  String _fmtDate(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    if (_property == null || _partner == null) {
      setState(() => _error = 'Selecciona propiedad y cliente.');
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });

    final vals = {
      'property_id': _property!.id,
      'partner_id': _partner!.id,
      'contract_type': _contractType,
      'date_start': _fmtDate(_dateStart),
      if (_dateEnd != null) 'date_end': _fmtDate(_dateEnd!),
      'amount': double.tryParse(_amountCtrl.text.trim()) ?? 0.0,
      'commission_percentage':
          double.tryParse(_commissionCtrl.text.trim()) ?? 5.0,
      if (!widget.isEdit) 'state': 'draft',
    };

    try {
      if (widget.isEdit) {
        await _service.update(widget.existing!.id, vals);
      } else {
        await _service.create(vals);
      }
      if (mounted) Navigator.of(context).pop(true);
    } catch (e) {
      setState(
        () => _error = 'No se pudo guardar el contrato. Intenta de nuevo.',
      );
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.isEdit ? 'Editar contrato' : 'Nuevo contrato'),
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(18),
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
            const SizedBox(height: 14),
            Many2oneField(
              label: 'Cliente',
              required: true,
              odoo: _odoo,
              model: 'res.partner',
              value: _partner,
              onChanged: (v) => setState(() => _partner = v),
            ),
            const SizedBox(height: 14),
            SelectField(
              label: 'Tipo de contrato',
              value: _contractType,
              options: ContractTypeStyle.options,
              onChanged: (v) =>
                  setState(() => _contractType = v ?? 'exclusive_owner'),
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: InkWell(
                    borderRadius: BorderRadius.circular(12),
                    onTap: () => _pickDate(isStart: true),
                    child: InputDecorator(
                      decoration: const InputDecoration(labelText: 'Inicio'),
                      child: Text(_fmtDate(_dateStart)),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: InkWell(
                    borderRadius: BorderRadius.circular(12),
                    onTap: () => _pickDate(isStart: false),
                    child: InputDecorator(
                      decoration: InputDecoration(
                        labelText: 'Fin',
                        suffixIcon: _dateEnd != null
                            ? IconButton(
                                icon: const Icon(Icons.close, size: 18),
                                onPressed: () =>
                                    setState(() => _dateEnd = null),
                              )
                            : null,
                      ),
                      child: Text(
                        _dateEnd != null ? _fmtDate(_dateEnd!) : 'Sin definir',
                        style: TextStyle(
                          color: _dateEnd != null
                              ? colors.ink
                              : colors.mutedLight,
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: _amountCtrl,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: 'Monto (\$)'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextFormField(
                    controller: _commissionCtrl,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    decoration: const InputDecoration(
                      labelText: 'Comisión (%)',
                    ),
                  ),
                ),
              ],
            ),
            if (_error != null) ...[
              const SizedBox(height: 12),
              Text(_error!, style: TextStyle(color: colors.danger)),
            ],
            const SizedBox(height: 24),
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
                  : Text(widget.isEdit ? 'Guardar cambios' : 'Crear contrato'),
            ),
          ],
        ),
      ),
    );
  }
}
