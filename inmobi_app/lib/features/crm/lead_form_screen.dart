import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api/odoo_client.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/many2one_field.dart';
import '../auth/auth_service.dart';
import 'lead_model.dart';
import 'lead_service.dart';

/// Crea o edita un lead/oportunidad (crm.lead). La puntuación (A/B/C) y la
/// temperatura NO se editan aquí a propósito: Odoo las calcula solo
/// (`_compute_lead_scoring`) a partir del presupuesto, el match y demás —
/// se recalculan al guardar, no son un campo que el usuario llene.
class LeadFormScreen extends StatefulWidget {
  final Lead? existing;
  final int? initialPropertyId;
  final String? initialPropertyName;

  const LeadFormScreen({
    super.key,
    this.existing,
    this.initialPropertyId,
    this.initialPropertyName,
  });

  bool get isEdit => existing != null;

  @override
  State<LeadFormScreen> createState() => _LeadFormScreenState();
}

class _LeadFormScreenState extends State<LeadFormScreen> {
  final _formKey = GlobalKey<FormState>();
  late final OdooClient _odoo;
  late final LeadService _service;

  final _nameCtrl = TextEditingController();
  final _contactCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  final _emailCtrl = TextEditingController();
  final _budgetCtrl = TextEditingController();
  final _preferredCityCtrl = TextEditingController();
  final _preferredBedroomsCtrl = TextEditingController();
  final _preferredMinAreaCtrl = TextEditingController();
  final _preferredMaxAreaCtrl = TextEditingController();
  final _clientNeedsCtrl = TextEditingController();
  final _descriptionCtrl = TextEditingController();
  Many2oneValue? _stage;
  Many2oneValue? _targetProperty;
  Many2oneValue? _partner;
  Many2oneValue? _preferredPropertyType;

  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _odoo = context.read<AuthService>().odoo;
    _service = LeadService(_odoo);
    final e = widget.existing;
    if (e != null) {
      _nameCtrl.text = e.name;
      _contactCtrl.text = e.contactName;
      _phoneCtrl.text = e.phone;
      _emailCtrl.text = e.email;
      _budgetCtrl.text = e.clientBudget > 0
          ? e.clientBudget.toStringAsFixed(0)
          : '';
      if (e.stageId != null) _stage = Many2oneValue(e.stageId!, e.stageName);
      if (e.targetPropertyId != null) {
        _targetProperty = Many2oneValue(
          e.targetPropertyId!,
          e.targetPropertyName,
        );
      }
      if (e.partnerId != null)
        _partner = Many2oneValue(e.partnerId!, e.partnerName);
      if (e.preferredPropertyTypeId != null) {
        _preferredPropertyType = Many2oneValue(
          e.preferredPropertyTypeId!,
          e.preferredPropertyTypeName,
        );
      }
      _preferredCityCtrl.text = e.preferredCity;
      _preferredBedroomsCtrl.text = e.preferredBedrooms > 0
          ? '${e.preferredBedrooms}'
          : '';
      _preferredMinAreaCtrl.text = e.preferredMinArea > 0
          ? e.preferredMinArea.toStringAsFixed(0)
          : '';
      _preferredMaxAreaCtrl.text = e.preferredMaxArea > 0
          ? e.preferredMaxArea.toStringAsFixed(0)
          : '';
      _clientNeedsCtrl.text = e.clientNeeds;
      _descriptionCtrl.text = e.description;
    } else if (widget.initialPropertyId != null) {
      _targetProperty = Many2oneValue(
        widget.initialPropertyId!,
        widget.initialPropertyName ?? 'Propiedad #${widget.initialPropertyId}',
      );
      _nameCtrl.text = 'Interesado en ${widget.initialPropertyName ?? 'Propiedad #${widget.initialPropertyId}'}';
    }
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _saving = true;
      _error = null;
    });

    final vals = {
      'name': _nameCtrl.text.trim(),
      'contact_name': _contactCtrl.text.trim(),
      'phone': _phoneCtrl.text.trim(),
      'email_from': _emailCtrl.text.trim(),
      'client_budget': double.tryParse(_budgetCtrl.text.trim()) ?? 0.0,
      if (_stage != null) 'stage_id': _stage!.id,
      'target_property_id': _targetProperty?.id ?? false,
      'partner_id': _partner?.id ?? false,
      'preferred_property_type_id': _preferredPropertyType?.id ?? false,
      'preferred_city': _preferredCityCtrl.text.trim(),
      'preferred_bedrooms':
          int.tryParse(_preferredBedroomsCtrl.text.trim()) ?? 0,
      'preferred_min_area':
          double.tryParse(_preferredMinAreaCtrl.text.trim()) ?? 0.0,
      'preferred_max_area':
          double.tryParse(_preferredMaxAreaCtrl.text.trim()) ?? 0.0,
      'client_needs': _clientNeedsCtrl.text.trim(),
      // El campo es Html en Odoo: se envuelven los saltos de línea en <p>
      // para que el chatter/formulario web lo muestre con el mismo formato.
      'description': _descriptionCtrl.text.trim().isEmpty
          ? false
          : _descriptionCtrl.text
                .trim()
                .split('\n')
                .map((line) => '<p>${line.isEmpty ? '<br>' : line}</p>')
                .join(),
    };

    try {
      if (widget.isEdit) {
        await _service.update(widget.existing!.id, vals);
      } else {
        await _service.create(vals);
      }
      if (mounted) Navigator.of(context).pop(true);
    } catch (e) {
      setState(() => _error = 'No se pudo guardar el lead. Intenta de nuevo.');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.isEdit ? 'Editar lead' : 'Nuevo lead')),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(18),
          children: [
            TextFormField(
              controller: _nameCtrl,
              decoration: const InputDecoration(
                labelText: 'Título de la oportunidad *',
              ),
              validator: (v) =>
                  (v == null || v.trim().isEmpty) ? 'Requerido' : null,
            ),
            const SizedBox(height: 14),
            TextFormField(
              controller: _contactCtrl,
              decoration: const InputDecoration(
                labelText: 'Nombre del cliente',
              ),
            ),
            const SizedBox(height: 14),
            TextFormField(
              controller: _phoneCtrl,
              keyboardType: TextInputType.phone,
              decoration: const InputDecoration(labelText: 'Teléfono'),
            ),
            const SizedBox(height: 14),
            TextFormField(
              controller: _emailCtrl,
              keyboardType: TextInputType.emailAddress,
              decoration: const InputDecoration(labelText: 'Email'),
            ),
            const SizedBox(height: 14),
            TextFormField(
              controller: _budgetCtrl,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Presupuesto del cliente (\$)',
              ),
            ),
            const SizedBox(height: 14),
            Many2oneField(
              label: 'Contacto vinculado',
              odoo: _odoo,
              model: 'res.partner',
              value: _partner,
              onChanged: (v) => setState(() => _partner = v),
            ),
            const _FormSectionTitle('Embudo'),
            Many2oneField(
              label: 'Etapa',
              odoo: _odoo,
              model: 'crm.stage',
              value: _stage,
              onChanged: (v) => setState(() => _stage = v),
            ),
            const _FormSectionTitle('Propiedad de interés'),
            Many2oneField(
              label: 'Propiedad de interés',
              odoo: _odoo,
              model: 'estate.property',
              searchField: 'title',
              value: _targetProperty,
              onChanged: (v) => setState(() => _targetProperty = v),
            ),
            const _FormSectionTitle('Preferencias del cliente'),
            Many2oneField(
              label: 'Tipo de propiedad preferido',
              odoo: _odoo,
              model: 'estate.property.type',
              value: _preferredPropertyType,
              onChanged: (v) => setState(() => _preferredPropertyType = v),
            ),
            const SizedBox(height: 14),
            TextFormField(
              controller: _preferredCityCtrl,
              decoration: const InputDecoration(labelText: 'Ciudad preferida'),
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: _preferredBedroomsCtrl,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Habitaciones',
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextFormField(
                    controller: _preferredMinAreaCtrl,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Área mín. (m²)',
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextFormField(
                    controller: _preferredMaxAreaCtrl,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Área máx. (m²)',
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            TextFormField(
              controller: _clientNeedsCtrl,
              minLines: 2,
              maxLines: 4,
              decoration: const InputDecoration(
                labelText: 'Necesidades especiales',
                alignLabelWithHint: true,
              ),
            ),
            const _FormSectionTitle('Notas internas'),
            TextFormField(
              controller: _descriptionCtrl,
              minLines: 4,
              maxLines: 10,
              decoration: const InputDecoration(
                hintText: 'Notas de seguimiento, acuerdos, observaciones...',
                alignLabelWithHint: true,
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: 12),
              Text(_error!, style: const TextStyle(color: AppColors.danger)),
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
                  : Text(widget.isEdit ? 'Guardar cambios' : 'Crear lead'),
            ),
          ],
        ),
      ),
    );
  }
}

class _FormSectionTitle extends StatelessWidget {
  final String title;
  const _FormSectionTitle(this.title);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 18, bottom: 14),
      child: Row(
        children: [
          Text(
            title,
            style: const TextStyle(
              fontWeight: FontWeight.w700,
              fontSize: 13,
              color: AppColors.navy,
            ),
          ),
          const SizedBox(width: 10),
          const Expanded(child: Divider(height: 1)),
        ],
      ),
    );
  }
}
