import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../core/api/odoo_client.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/many2one_field.dart';
import '../../core/widgets/select_field.dart';
import '../auth/auth_service.dart';
import 'reminder_model.dart';
import 'reminder_service.dart';

class ReminderFormScreen extends StatefulWidget {
  final Reminder? existing;
  final int? initialPartnerId;
  final String? initialPartnerName;
  final int? initialPropertyId;
  final String? initialPropertyName;

  const ReminderFormScreen({
    super.key,
    this.existing,
    this.initialPartnerId,
    this.initialPartnerName,
    this.initialPropertyId,
    this.initialPropertyName,
  });

  bool get isEdit => existing != null;

  @override
  State<ReminderFormScreen> createState() => _ReminderFormScreenState();
}

class _ReminderFormScreenState extends State<ReminderFormScreen> {
  final _formKey = GlobalKey<FormState>();
  late final OdooClient _odoo;
  late final ReminderService _service;

  final _nameCtrl = TextEditingController();
  final _noteCtrl = TextEditingController();

  Many2oneValue? _partner;
  Many2oneValue? _property;
  String _type = 'policy';
  DateTime _date = DateTime.now().add(const Duration(days: 30));
  int _daysBefore = 7;
  bool _notifyPush = true;

  bool _saving = false;
  String? _error;

  static const _defaultDaysOptions = [0, 1, 3, 7, 15, 30, 60, 90];

  // Si el recordatorio traía una anticipación fuera de la lista, se añade
  // para que el chip aparezca seleccionado en vez de perderse.
  List<int> get _daysOptions => _defaultDaysOptions.contains(_daysBefore)
      ? _defaultDaysOptions
      : ([..._defaultDaysOptions, _daysBefore]..sort());

  @override
  void initState() {
    super.initState();
    _odoo = context.read<AuthService>().odoo;
    _service = ReminderService(_odoo);

    final e = widget.existing;
    if (e != null) {
      _nameCtrl.text = e.name;
      _noteCtrl.text = e.note;
      _type = e.reminderType;
      _daysBefore = e.daysBefore;
      _notifyPush = e.notifyPush;
      if (e.date != null) _date = e.date!;
      if (e.partnerId != null) {
        _partner = Many2oneValue(e.partnerId!, e.partnerName);
      }
      if (e.propertyId != null) {
        _property = Many2oneValue(e.propertyId!, e.propertyName);
      }
    } else {
      if (widget.initialPartnerId != null) {
        _partner = Many2oneValue(
          widget.initialPartnerId!,
          widget.initialPartnerName ?? '',
        );
      }
      if (widget.initialPropertyId != null) {
        _property = Many2oneValue(
          widget.initialPropertyId!,
          widget.initialPropertyName ?? '',
        );
      }
    }
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _noteCtrl.dispose();
    super.dispose();
  }

  DateTime get _notifyOn => _date.subtract(Duration(days: _daysBefore));

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _date,
      firstDate: DateTime.now().subtract(const Duration(days: 365)),
      lastDate: DateTime.now().add(const Duration(days: 365 * 5)),
    );
    if (picked != null) setState(() => _date = picked);
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    if (_partner == null) {
      setState(() => _error = 'Elige el cliente del recordatorio.');
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });

    final vals = <String, dynamic>{
      'name': _nameCtrl.text.trim(),
      'reminder_type': _type,
      'partner_id': _partner!.id,
      'property_id': _property?.id ?? false,
      'date': ReminderService.formatDate(_date),
      'days_before': _daysBefore,
      'notify_push': _notifyPush,
      'note': _noteCtrl.text.trim(),
      if (!widget.isEdit && _odoo.userId != null) 'user_id': _odoo.userId,
    };

    try {
      if (widget.isEdit) {
        await _service.update(widget.existing!.id, vals);
      } else {
        await _service.create(vals);
      }
      if (mounted) Navigator.of(context).pop(true);
    } catch (_) {
      setState(() => _error = 'No se pudo guardar el recordatorio.');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.of(context);
    final dateFmt = DateFormat("EEEE d 'de' MMMM, y", 'es_EC');
    final shortFmt = DateFormat('d MMM y', 'es_EC');

    return Scaffold(
      appBar: AppBar(
        title: Text(
          widget.isEdit ? 'Editar recordatorio' : 'Nuevo recordatorio',
        ),
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(18),
          children: [
            TextFormField(
              controller: _nameCtrl,
              textCapitalization: TextCapitalization.sentences,
              decoration: const InputDecoration(
                labelText: 'Asunto *',
                hintText: 'Ej: Vence la póliza de incendios',
              ),
              validator: (v) =>
                  (v == null || v.trim().isEmpty) ? 'Escribe un asunto' : null,
            ),
            const SizedBox(height: 14),
            SelectField(
              label: 'Tipo',
              value: _type,
              options: ReminderTypeStyle.options,
              onChanged: (v) => setState(() => _type = v ?? 'other'),
            ),
            const SizedBox(height: 14),
            Many2oneField(
              label: 'Cliente',
              odoo: _odoo,
              model: 'res.partner',
              searchField: 'name',
              required: true,
              value: _partner,
              onChanged: (v) => setState(() => _partner = v),
            ),
            const SizedBox(height: 14),
            Many2oneField(
              label: 'Propiedad relacionada',
              odoo: _odoo,
              model: 'estate.property',
              searchField: 'title',
              value: _property,
              onChanged: (v) => setState(() => _property = v),
            ),

            const SizedBox(height: 22),
            Text(
              '¿CUÁNDO AVISAR?',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w800,
                letterSpacing: 0.8,
                color: colors.muted,
              ),
            ),
            const SizedBox(height: 10),
            InkWell(
              onTap: _pickDate,
              borderRadius: BorderRadius.circular(12),
              child: InputDecorator(
                decoration: const InputDecoration(
                  labelText: 'Fecha del vencimiento',
                  prefixIcon: Icon(Icons.event_outlined),
                ),
                child: Text(
                  dateFmt.format(_date),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ),
            const SizedBox(height: 14),
            Text(
              'Avisarme con anticipación',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: colors.muted,
              ),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: _daysOptions.map((d) {
                final selected = _daysBefore == d;
                return ChoiceChip(
                  label: Text(d == 0 ? 'El mismo día' : '$d días antes'),
                  selected: selected,
                  onSelected: (_) => setState(() => _daysBefore = d),
                );
              }).toList(),
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: colors.infoBg,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  Icon(
                    Icons.notifications_active_outlined,
                    size: 18,
                    color: colors.info,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      _daysBefore == 0
                          ? 'Recibirás el aviso el mismo ${shortFmt.format(_date)}.'
                          : 'Recibirás el aviso el ${shortFmt.format(_notifyOn)} '
                                'y otro el día del vencimiento.',
                      style: TextStyle(fontSize: 12.5, color: colors.info),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 6),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              value: _notifyPush,
              onChanged: (v) => setState(() => _notifyPush = v),
              title: const Text(
                'Notificación en el celular',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
              ),
              subtitle: Text(
                'Además del aviso dentro de Odoo.',
                style: TextStyle(fontSize: 12, color: colors.muted),
              ),
            ),

            const SizedBox(height: 12),
            TextFormField(
              controller: _noteCtrl,
              maxLines: 4,
              textCapitalization: TextCapitalization.sentences,
              decoration: const InputDecoration(
                labelText: 'Notas',
                hintText: 'N° de póliza, aseguradora, contacto...',
                alignLabelWithHint: true,
              ),
            ),

            if (_error != null) ...[
              const SizedBox(height: 14),
              Text(
                _error!,
                style: TextStyle(color: colors.danger, fontSize: 13),
              ),
            ],
            const SizedBox(height: 22),
            FilledButton.icon(
              onPressed: _saving ? null : _save,
              icon: _saving
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Icon(Icons.check_rounded),
              label: Text(_saving ? 'Guardando...' : 'Guardar recordatorio'),
            ),
            const SizedBox(height: 30),
          ],
        ),
      ),
    );
  }
}
