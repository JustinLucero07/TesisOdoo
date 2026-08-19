import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../core/api/odoo_client.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/many2one_field.dart';
import '../../core/widgets/select_field.dart';
import '../auth/auth_service.dart';
import 'visit_model.dart';
import 'visit_service.dart';

/// Crea o edita una cita (calendar.event) — mismo modelo que usa el
/// calendario nativo de Odoo y la sincronización con Google Calendar; una
/// visita creada aquí aparece igual en el ERP y se sincroniza igual.
class VisitFormScreen extends StatefulWidget {
  final Visit? existing;
  // Precarga al agendar desde una propiedad o desde un lead, para no
  // obligar a volver a buscar lo que ya se sabe.
  final int? initialPropertyId;
  final String? initialPropertyName;
  final int? initialClientId;
  final String? initialClientName;

  const VisitFormScreen({
    super.key,
    this.existing,
    this.initialPropertyId,
    this.initialPropertyName,
    this.initialClientId,
    this.initialClientName,
  });

  bool get isEdit => existing != null;

  @override
  State<VisitFormScreen> createState() => _VisitFormScreenState();
}

class _VisitFormScreenState extends State<VisitFormScreen> {
  final _formKey = GlobalKey<FormState>();
  late final OdooClient _odoo;
  late final VisitService _service;

  Many2oneValue? _property;
  Many2oneValue? _client;
  DateTime _date = DateTime.now();
  TimeOfDay _time = TimeOfDay.now();
  String _appointmentType = 'visit';
  String _visitState = 'scheduled';
  final _notesCtrl = TextEditingController();
  final _locationCtrl = TextEditingController();
  final _reminderValueCtrl = TextEditingController();
  String _reminderUnit = 'hours';

  bool _saving = false;
  String? _error;

  static const _typeOptions = [
    ('visit', 'Visita'),
    ('meeting', 'Reunión'),
    ('call', 'Llamada'),
    ('signing', 'Firma de contrato'),
  ];

  static const _stateOptions = [
    ('scheduled', 'Programada'),
    ('done', 'Realizada'),
    ('cancelled', 'Cancelada'),
  ];

  @override
  void initState() {
    super.initState();
    _odoo = context.read<AuthService>().odoo;
    _service = VisitService(_odoo);
    final e = widget.existing;
    if (e != null) {
      _date = e.start;
      _time = TimeOfDay.fromDateTime(e.start);
      _appointmentType = e.appointmentType;
      _visitState = e.visitState;
      _notesCtrl.text = e.notes;
      _locationCtrl.text = e.location;
      if (e.reminderValue > 0) {
        _reminderValueCtrl.text = '${e.reminderValue}';
        _reminderUnit = e.reminderUnit;
      }
      if (e.propertyId != null) {
        _property = Many2oneValue(e.propertyId!, e.propertyName);
      }
      if (e.clientId != null) {
        _client = Many2oneValue(e.clientId!, e.clientName);
      }
    } else {
      if (widget.initialPropertyId != null) {
        _property = Many2oneValue(
          widget.initialPropertyId!,
          widget.initialPropertyName ?? '',
        );
      }
      if (widget.initialClientId != null) {
        _client = Many2oneValue(
          widget.initialClientId!,
          widget.initialClientName ?? '',
        );
      }
    }
  }

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _date,
      firstDate: DateTime.now().subtract(const Duration(days: 365)),
      lastDate: DateTime.now().add(const Duration(days: 730)),
    );
    if (picked != null) setState(() => _date = picked);
  }

  Future<void> _pickTime() async {
    final picked = await showTimePicker(context: context, initialTime: _time);
    if (picked != null) setState(() => _time = picked);
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    if (_property == null) {
      setState(() => _error = 'Elige una propiedad.');
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });

    final start = DateTime(
      _date.year,
      _date.month,
      _date.day,
      _time.hour,
      _time.minute,
    );
    final stop = start.add(const Duration(hours: 1));
    final vals = {
      'name': 'Visita: ${_property!.name}',
      'start': VisitService.formatUtc(start),
      'stop': VisitService.formatUtc(stop),
      'appointment_type': _appointmentType,
      'property_id': _property!.id,
      if (_client != null) 'client_id': _client!.id,
      'visit_notes': _notesCtrl.text.trim(),
      'location': _locationCtrl.text.trim(),
      // Anticipación del recordatorio de WhatsApp para ESTA cita; si se deja
      // vacío, el ERP usa la del asesor o la general de Ajustes.
      'whatsapp_reminder_value':
          int.tryParse(_reminderValueCtrl.text.trim()) ?? 0,
      'whatsapp_reminder_unit': _reminderUnit,
      if (widget.isEdit) 'visit_state': _visitState,
    };

    try {
      if (widget.isEdit) {
        await _service.update(widget.existing!.id, vals);
      } else {
        await _service.create(vals);
      }
      if (mounted) Navigator.of(context).pop(true);
    } catch (e) {
      setState(() => _error = 'No se pudo guardar la cita. Intenta de nuevo.');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final dateFmt = DateFormat("EEEE d 'de' MMMM, y", 'es_EC');
    return Scaffold(
      appBar: AppBar(title: Text(widget.isEdit ? 'Editar cita' : 'Nueva cita')),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(18),
          children: [
            Many2oneField(
              label: 'Propiedad',
              odoo: _odoo,
              model: 'estate.property',
              searchField: 'title',
              required: true,
              value: _property,
              onChanged: (v) => setState(() => _property = v),
            ),
            const SizedBox(height: 14),
            Many2oneField(
              label: 'Cliente',
              odoo: _odoo,
              model: 'res.partner',
              searchField: 'name',
              value: _client,
              onChanged: (v) => setState(() => _client = v),
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: InkWell(
                    onTap: _pickDate,
                    borderRadius: BorderRadius.circular(12),
                    child: InputDecorator(
                      decoration: const InputDecoration(
                        labelText: 'Fecha',
                        prefixIcon: Icon(Icons.calendar_today_outlined),
                      ),
                      child: Text(
                        dateFmt.format(_date),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: InkWell(
                    onTap: _pickTime,
                    borderRadius: BorderRadius.circular(12),
                    child: InputDecorator(
                      decoration: const InputDecoration(
                        labelText: 'Hora',
                        prefixIcon: Icon(Icons.schedule),
                      ),
                      child: Text(_time.format(context)),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            SelectField(
              label: 'Tipo de cita',
              value: _appointmentType,
              options: _typeOptions,
              onChanged: (v) => setState(() => _appointmentType = v ?? 'visit'),
            ),
            if (widget.isEdit) ...[
              const SizedBox(height: 14),
              SelectField(
                label: 'Estado',
                value: _visitState,
                options: _stateOptions,
                onChanged: (v) =>
                    setState(() => _visitState = v ?? 'scheduled'),
              ),
            ],
            const SizedBox(height: 14),
            TextFormField(
              controller: _locationCtrl,
              decoration: const InputDecoration(
                labelText: 'Lugar de encuentro',
                prefixIcon: Icon(Icons.place_outlined),
              ),
            ),
            const SizedBox(height: 14),
            // Recordatorio de WhatsApp propio de esta cita. Vacío = se usa
            // el del asesor, o el general configurado en el ERP.
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: _reminderValueCtrl,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Recordar antes de',
                      hintText: 'Automático',
                      prefixIcon: Icon(Icons.notifications_active_outlined),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: SelectField(
                    label: 'Unidad',
                    value: _reminderUnit,
                    options: ReminderUnitStyle.options,
                    onChanged: (v) =>
                        setState(() => _reminderUnit = v ?? 'hours'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            TextFormField(
              controller: _notesCtrl,
              minLines: 3,
              maxLines: 6,
              decoration: const InputDecoration(
                labelText: 'Notas',
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
                  : Text(widget.isEdit ? 'Guardar cambios' : 'Crear cita'),
            ),
          ],
        ),
      ),
    );
  }
}
