import 'dart:convert';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/api/odoo_client.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/many2one_field.dart';
import 'document_model.dart';
import 'document_service.dart';

class DocumentFormScreen extends StatefulWidget {
  final OdooClient odoo;
  final DocumentOwner? initialOwner;
  final EstateDocument? existing;

  const DocumentFormScreen({
    super.key,
    required this.odoo,
    this.initialOwner,
    this.existing,
  });

  bool get isEdit => existing != null;

  @override
  State<DocumentFormScreen> createState() => _DocumentFormScreenState();
}

class _DocumentFormScreenState extends State<DocumentFormScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameCtrl = TextEditingController();

  Many2oneValue? _type;
  String _confidentiality = 'internal';
  String _state = 'received';
  DateTime _date = DateTime.now();
  DateTime? _expirationDate;

  Many2oneValue? _property;
  Many2oneValue? _partner;
  Many2oneValue? _contract;
  Many2oneValue? _lead;

  PlatformFile? _selectedFile;
  bool _saving = false;
  String? _error;

  static const _confidentialityOptions = [
    ('internal', 'Interno (todos los asesores)'),
    ('public', 'Público'),
    ('restricted', 'Restringido (asesor + manager)'),
    ('confidential', 'Confidencial (solo manager y admin)'),
  ];

  static const _stateOptions = [
    ('received', 'Recibido'),
    ('pending', 'Pendiente (sin archivo aún)'),
    ('verified', 'Verificado'),
    ('archived', 'Archivado'),
  ];

  @override
  void initState() {
    super.initState();
    final doc = widget.existing;
    if (doc != null) {
      _nameCtrl.text = doc.name;
      if (doc.typeId != null) {
        _type = Many2oneValue(doc.typeId!, doc.typeName);
      }
      _confidentiality = doc.confidentiality;
      _state = doc.state;
      if (doc.date != null) _date = doc.date!;
      _expirationDate = doc.expirationDate;

      if (doc.propertyId != null) {
        _property = Many2oneValue(doc.propertyId!, doc.propertyName);
      }
      if (doc.partnerId != null) {
        _partner = Many2oneValue(doc.partnerId!, doc.partnerName);
      }
      if (doc.contractId != null) {
        _contract = Many2oneValue(doc.contractId!, doc.contractName);
      }
      if (doc.leadId != null) {
        _lead = Many2oneValue(doc.leadId!, doc.leadName);
      }
    } else if (widget.initialOwner != null) {
      final owner = widget.initialOwner!;
      if (owner.field == 'property_id') {
        _property = Many2oneValue(owner.id, 'Propiedad #${owner.id}');
        _loadOwnerName('estate.property', owner.id, (name) {
          if (mounted)
            setState(() => _property = Many2oneValue(owner.id, name));
        });
      } else if (owner.field == 'partner_id') {
        _partner = Many2oneValue(owner.id, 'Contacto #${owner.id}');
        _loadOwnerName('res.partner', owner.id, (name) {
          if (mounted) setState(() => _partner = Many2oneValue(owner.id, name));
        });
      } else if (owner.field == 'contract_id') {
        _contract = Many2oneValue(owner.id, 'Contrato #${owner.id}');
        _loadOwnerName('estate.contract', owner.id, (name) {
          if (mounted)
            setState(() => _contract = Many2oneValue(owner.id, name));
        });
      } else if (owner.field == 'lead_id') {
        _lead = Many2oneValue(owner.id, 'Lead #${owner.id}');
        _loadOwnerName('crm.lead', owner.id, (name) {
          if (mounted) setState(() => _lead = Many2oneValue(owner.id, name));
        });
      }
    }
  }

  Future<void> _loadOwnerName(
    String model,
    int id,
    Function(String) onLoaded,
  ) async {
    try {
      final rows = await widget.odoo.searchRead(
        model: model,
        domain: [
          ['id', '=', id],
        ],
        fields: ['name', if (model == 'estate.property') 'title'],
        limit: 1,
      );
      if (rows.isNotEmpty) {
        final r = rows.first;
        final name = (r['name'] ?? r['title'] ?? '').toString();
        if (name.isNotEmpty) onLoaded(name);
      }
    } catch (_) {}
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    super.dispose();
  }

  Future<void> _pickFile() async {
    final picked = await FilePicker.platform.pickFiles(withData: true);
    if (picked != null && picked.files.isNotEmpty) {
      final f = picked.files.single;
      setState(() {
        _selectedFile = f;
        if (_nameCtrl.text.trim().isEmpty) {
          _nameCtrl.text = f.name;
        }
        if (_state == 'pending') {
          _state = 'received';
        }
      });
    }
  }

  Future<void> _selectDate({required bool isExpiration}) async {
    final initial = isExpiration
        ? (_expirationDate ?? DateTime.now().add(const Duration(days: 365)))
        : _date;
    final picked = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
    );
    if (picked != null) {
      setState(() {
        if (isExpiration) {
          _expirationDate = picked;
        } else {
          _date = picked;
        }
      });
    }
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;

    if (_type == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Por favor selecciona el tipo de documento.'),
        ),
      );
      return;
    }

    setState(() {
      _saving = true;
      _error = null;
    });

    final vals = <String, dynamic>{
      'name': _nameCtrl.text.trim(),
      'type_id': _type!.id,
      'confidentiality': _confidentiality,
      'state': _state,
      'date': DateFormat('yyyy-MM-dd').format(_date),
      if (_expirationDate != null)
        'expiration_date': DateFormat('yyyy-MM-dd').format(_expirationDate!)
      else if (widget.isEdit)
        'expiration_date': false,
      if (_property != null)
        'property_id': _property!.id
      else if (widget.isEdit)
        'property_id': false,
      if (_partner != null)
        'partner_id': _partner!.id
      else if (widget.isEdit)
        'partner_id': false,
      if (_contract != null)
        'contract_id': _contract!.id
      else if (widget.isEdit)
        'contract_id': false,
      if (_lead != null)
        'lead_id': _lead!.id
      else if (widget.isEdit)
        'lead_id': false,
    };

    if (_selectedFile != null && _selectedFile!.bytes != null) {
      vals['file'] = base64Encode(_selectedFile!.bytes!);
      vals['filename'] = _selectedFile!.name;
      if (_state == 'pending') vals['state'] = 'received';
    }

    try {
      if (widget.isEdit) {
        await widget.odoo.write(
          model: 'estate.document',
          id: widget.existing!.id,
          values: vals,
        );
      } else {
        await widget.odoo.create(model: 'estate.document', values: vals);
      }

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              widget.isEdit
                  ? 'Documento actualizado.'
                  : 'Documento guardado en Odoo.',
            ),
            backgroundColor: AppColors.of(context).success,
          ),
        );
        Navigator.of(context).pop(true);
      }
    } catch (e) {
      final msg = e.toString().replaceAll('Exception:', '').trim();
      setState(
        () => _error = msg.isNotEmpty
            ? msg
            : 'No se pudo guardar el documento en Odoo.',
      );
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final dateFmt = DateFormat('d MMMM y', 'es_EC');
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colors = AppColors.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.isEdit ? 'Editar Documento' : 'Nuevo Documento'),
        actions: [
          if (_saving)
            const Center(
              child: Padding(
                padding: EdgeInsets.symmetric(horizontal: 16),
                child: SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: Colors.white,
                  ),
                ),
              ),
            )
          else
            TextButton(
              onPressed: _save,
              child: const Text(
                'Guardar',
                style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
              ),
            ),
        ],
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(18),
          children: [
            if (_error != null) ...[
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: colors.danger.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: colors.danger.withValues(alpha: 0.4),
                  ),
                ),
                child: Row(
                  children: [
                    Icon(Icons.error_outline, color: colors.danger, size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _error!,
                        style: TextStyle(color: colors.danger, fontSize: 13),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
            ],

            TextFormField(
              controller: _nameCtrl,
              decoration: const InputDecoration(
                labelText: 'Nombre del Documento *',
                hintText: 'Ej: Escritura Notariada, Pago Predial 2026',
                prefixIcon: Icon(Icons.description_outlined),
              ),
              validator: (v) => (v == null || v.trim().isEmpty)
                  ? 'Ingresa el nombre del documento'
                  : null,
            ),
            const SizedBox(height: 14),

            Many2oneField(
              label: 'Tipo de Documento *',
              required: true,
              odoo: widget.odoo,
              model: 'estate.document.type',
              value: _type,
              onChanged: (v) => setState(() => _type = v),
            ),
            const SizedBox(height: 14),

            const _FormSectionTitle('Archivo Adjunto'),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: isDark
                    ? const Color(0xFF1E1A3E)
                    : const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(
                  color: isDark ? Colors.white12 : const Color(0xFFE2E8F0),
                ),
              ),
              child: Column(
                children: [
                  if (_selectedFile != null) ...[
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: const Color(
                              0xFF10B981,
                            ).withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: const Icon(
                            Icons.file_present_rounded,
                            color: Color(0xFF10B981),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                _selectedFile!.name,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w700,
                                  fontSize: 13,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                              Text(
                                '${(_selectedFile!.size / (1024 * 1024)).toStringAsFixed(2)} MB',
                                style: TextStyle(
                                  color: colors.muted,
                                  fontSize: 11.5,
                                ),
                              ),
                            ],
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.close_rounded, size: 20),
                          onPressed: () => setState(() => _selectedFile = null),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                  ] else if (widget.isEdit &&
                      widget.existing!.filename.isNotEmpty) ...[
                    Row(
                      children: [
                        Icon(widget.existing!.icon, color: colors.navy),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            widget.existing!.filename,
                            style: const TextStyle(
                              fontWeight: FontWeight.w600,
                              fontSize: 13,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                  ],
                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton.icon(
                      onPressed: _pickFile,
                      icon: const Icon(Icons.upload_file_rounded, size: 18),
                      label: Text(
                        _selectedFile != null ||
                                (widget.isEdit &&
                                    widget.existing!.filename.isNotEmpty)
                            ? 'Cambiar Archivo'
                            : 'Seleccionar Archivo (PDF, Imagen, Doc)',
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),

            const _FormSectionTitle('Clasificación y Estado'),
            DropdownButtonFormField<String>(
              initialValue: _confidentiality,
              decoration: const InputDecoration(
                labelText: 'Nivel de Confidencialidad',
                prefixIcon: Icon(Icons.security_outlined),
              ),
              items: _confidentialityOptions
                  .map(
                    (opt) => DropdownMenuItem(
                      value: opt.$1,
                      child: Text(opt.$2, style: const TextStyle(fontSize: 13)),
                    ),
                  )
                  .toList(),
              onChanged: (v) {
                if (v != null) setState(() => _confidentiality = v);
              },
            ),
            const SizedBox(height: 14),

            DropdownButtonFormField<String>(
              initialValue: _state,
              decoration: const InputDecoration(
                labelText: 'Estado del Documento',
                prefixIcon: Icon(Icons.rule_outlined),
              ),
              items: _stateOptions
                  .map(
                    (opt) => DropdownMenuItem(
                      value: opt.$1,
                      child: Text(opt.$2, style: const TextStyle(fontSize: 13)),
                    ),
                  )
                  .toList(),
              onChanged: (v) {
                if (v != null) setState(() => _state = v);
              },
            ),
            const SizedBox(height: 14),

            const _FormSectionTitle('Fechas'),
            Row(
              children: [
                Expanded(
                  child: InkWell(
                    onTap: () => _selectDate(isExpiration: false),
                    borderRadius: BorderRadius.circular(10),
                    child: InputDecorator(
                      decoration: const InputDecoration(
                        labelText: 'Fecha del Documento',
                        prefixIcon: Icon(
                          Icons.calendar_today_outlined,
                          size: 18,
                        ),
                      ),
                      child: Text(
                        dateFmt.format(_date),
                        style: const TextStyle(fontSize: 13),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: InkWell(
                    onTap: () => _selectDate(isExpiration: true),
                    borderRadius: BorderRadius.circular(10),
                    child: InputDecorator(
                      decoration: InputDecoration(
                        labelText: 'Vencimiento (Opcional)',
                        prefixIcon: const Icon(
                          Icons.event_busy_outlined,
                          size: 18,
                        ),
                        suffixIcon: _expirationDate != null
                            ? IconButton(
                                icon: const Icon(Icons.clear, size: 16),
                                onPressed: () =>
                                    setState(() => _expirationDate = null),
                              )
                            : null,
                      ),
                      child: Text(
                        _expirationDate != null
                            ? dateFmt.format(_expirationDate!)
                            : 'Sin vencimiento',
                        style: TextStyle(
                          fontSize: 13,
                          color: _expirationDate != null
                              ? null
                              : colors.mutedLight,
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),

            const _FormSectionTitle('Vinculación (Odoo)'),
            Many2oneField(
              label: 'Propiedad vinculada',
              odoo: widget.odoo,
              model: 'estate.property',
              searchField: 'title',
              value: _property,
              onChanged: (v) => setState(() => _property = v),
            ),
            const SizedBox(height: 12),
            Many2oneField(
              label: 'Cliente / Contacto vinculado',
              odoo: widget.odoo,
              model: 'res.partner',
              value: _partner,
              onChanged: (v) => setState(() => _partner = v),
            ),
            const SizedBox(height: 12),
            Many2oneField(
              label: 'Contrato vinculado',
              odoo: widget.odoo,
              model: 'estate.contract',
              value: _contract,
              onChanged: (v) => setState(() => _contract = v),
            ),
            const SizedBox(height: 12),
            Many2oneField(
              label: 'Oportunidad / Lead vinculado',
              odoo: widget.odoo,
              model: 'crm.lead',
              value: _lead,
              onChanged: (v) => setState(() => _lead = v),
            ),

            const SizedBox(height: 24),
            FilledButton.icon(
              style: FilledButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              onPressed: _saving ? null : _save,
              icon: _saving
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Icon(Icons.save_outlined),
              label: Text(
                widget.isEdit
                    ? 'Actualizar Documento'
                    : 'Guardar Documento en Odoo',
                style: const TextStyle(
                  fontWeight: FontWeight.w700,
                  fontSize: 15,
                ),
              ),
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
      padding: const EdgeInsets.only(top: 8, bottom: 8),
      child: Text(
        title,
        style: TextStyle(
          fontWeight: FontWeight.w800,
          fontSize: 13,
          color: AppColors.of(context).muted,
        ),
      ),
    );
  }
}
