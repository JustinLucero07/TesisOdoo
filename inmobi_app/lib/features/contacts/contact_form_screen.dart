import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api/odoo_client.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/select_field.dart';
import '../auth/auth_service.dart';
import 'contact_model.dart';
import 'contact_service.dart';

/// Crea o edita un contacto (`res.partner`) con los campos inmobiliarios
/// que agrega el ERP. Los contadores (propiedades, contratos) no se editan:
/// son calculados por Odoo.
class ContactFormScreen extends StatefulWidget {
  final Contact? existing;
  const ContactFormScreen({super.key, this.existing});

  bool get isEdit => existing != null;

  @override
  State<ContactFormScreen> createState() => _ContactFormScreenState();
}

class _ContactFormScreenState extends State<ContactFormScreen> {
  final _formKey = GlobalKey<FormState>();
  late final ContactService _service;

  final _nameCtrl = TextEditingController();
  final _mobileCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  final _emailCtrl = TextEditingController();
  final _cityCtrl = TextEditingController();
  final _streetCtrl = TextEditingController();
  final _vatCtrl = TextEditingController();
  final _idNumberCtrl = TextEditingController();
  final _professionCtrl = TextEditingController();
  final _functionCtrl = TextEditingController();
  String _idType = 'cedula';
  String _preferredContact = 'whatsapp';
  bool _isCompany = false;
  bool _isPropertyOwner = false;
  bool _isAlliedAgency = false;

  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    final OdooClient odoo = context.read<AuthService>().odoo;
    _service = ContactService(odoo);
    final c = widget.existing;
    if (c != null) {
      _nameCtrl.text = c.name;
      _mobileCtrl.text = c.mobile;
      _phoneCtrl.text = c.phone;
      _emailCtrl.text = c.email;
      _cityCtrl.text = c.city;
      _streetCtrl.text = c.street;
      _vatCtrl.text = c.vat;
      _idNumberCtrl.text = c.idNumber;
      _professionCtrl.text = c.profession;
      _functionCtrl.text = c.function;
      if (c.idType.isNotEmpty) _idType = c.idType;
      if (c.preferredContact.isNotEmpty) _preferredContact = c.preferredContact;
      _isCompany = c.isCompany;
      _isPropertyOwner = c.isPropertyOwner;
      _isAlliedAgency = c.isAlliedAgency;
    }
  }

  @override
  void dispose() {
    for (final ctrl in [
      _nameCtrl,
      _mobileCtrl,
      _phoneCtrl,
      _emailCtrl,
      _cityCtrl,
      _streetCtrl,
      _vatCtrl,
      _idNumberCtrl,
      _professionCtrl,
      _functionCtrl,
    ]) {
      ctrl.dispose();
    }
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _saving = true;
      _error = null;
    });

    final mobile = _mobileCtrl.text.trim();
    final phone = _phoneCtrl.text.trim();
    final effectivePhone = phone.isNotEmpty ? phone : mobile;
    final effectiveMobile = mobile.isNotEmpty ? mobile : phone;

    final vals = {
      'name': _nameCtrl.text.trim(),
      'mobile': effectiveMobile,
      'phone': effectivePhone,
      'email': _emailCtrl.text.trim(),
      'city': _cityCtrl.text.trim(),
      'street': _streetCtrl.text.trim(),
      'vat': _vatCtrl.text.trim(),
      'id_number': _idNumberCtrl.text.trim(),
      'id_type': _idType,
      'profession': _professionCtrl.text.trim(),
      'function': _functionCtrl.text.trim(),
      'preferred_contact': _preferredContact,
      'is_company': _isCompany,
      'is_property_owner': _isPropertyOwner,
      'is_allied_agency': _isAlliedAgency,
    };

    try {
      if (widget.isEdit) {
        await _service.update(widget.existing!.id, vals);
        if (mounted) Navigator.of(context).pop(true);
      } else {
        final newId = await _service.create(vals);
        if (mounted) Navigator.of(context).pop(newId);
      }
    } catch (e) {
      if (mounted) {
        setState(
          () => _error = 'No se pudo guardar el contacto. Intenta de nuevo.',
        );
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.isEdit ? 'Editar contacto' : 'Nuevo contacto'),
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(18),
          children: [
            TextFormField(
              controller: _nameCtrl,
              decoration: const InputDecoration(labelText: 'Nombre *'),
              validator: (v) =>
                  (v == null || v.trim().isEmpty) ? 'Requerido' : null,
            ),
            const _FormSectionTitle('Contacto'),
            TextFormField(
              controller: _mobileCtrl,
              keyboardType: TextInputType.phone,
              decoration: const InputDecoration(labelText: 'Celular'),
            ),
            const SizedBox(height: 14),
            TextFormField(
              controller: _phoneCtrl,
              keyboardType: TextInputType.phone,
              decoration: const InputDecoration(labelText: 'Teléfono fijo'),
            ),
            const SizedBox(height: 14),
            TextFormField(
              controller: _emailCtrl,
              keyboardType: TextInputType.emailAddress,
              decoration: const InputDecoration(labelText: 'Email'),
            ),
            const SizedBox(height: 14),
            SelectField(
              label: 'Preferencia de contacto',
              value: _preferredContact,
              options: ContactPreferredContactStyle.options,
              onChanged: (v) =>
                  setState(() => _preferredContact = v ?? 'whatsapp'),
            ),
            const _FormSectionTitle('Identificación'),
            SelectField(
              label: 'Tipo de documento',
              value: _idType,
              options: ContactIdTypeStyle.options,
              onChanged: (v) => setState(() => _idType = v ?? 'cedula'),
            ),
            const SizedBox(height: 14),
            TextFormField(
              controller: _idNumberCtrl,
              decoration: const InputDecoration(
                labelText: 'Número de documento',
              ),
            ),
            const SizedBox(height: 14),
            TextFormField(
              controller: _vatCtrl,
              decoration: const InputDecoration(labelText: 'RUC / NIF'),
            ),
            const SizedBox(height: 14),
            TextFormField(
              controller: _professionCtrl,
              decoration: const InputDecoration(
                labelText: 'Profesión / Ocupación',
              ),
            ),
            const SizedBox(height: 14),
            TextFormField(
              controller: _functionCtrl,
              decoration: const InputDecoration(labelText: 'Cargo'),
            ),
            const _FormSectionTitle('Dirección'),
            TextFormField(
              controller: _streetCtrl,
              decoration: const InputDecoration(labelText: 'Calle'),
            ),
            const SizedBox(height: 14),
            TextFormField(
              controller: _cityCtrl,
              decoration: const InputDecoration(labelText: 'Ciudad'),
            ),
            const _FormSectionTitle('Tipo de contacto'),
            SwitchListTile.adaptive(
              contentPadding: EdgeInsets.zero,
              title: const Text(
                'Es una empresa',
                style: TextStyle(fontSize: 14),
              ),
              value: _isCompany,
              onChanged: (v) => setState(() => _isCompany = v),
            ),
            SwitchListTile.adaptive(
              contentPadding: EdgeInsets.zero,
              title: const Text(
                'Es propietario de inmuebles',
                style: TextStyle(fontSize: 14),
              ),
              value: _isPropertyOwner,
              onChanged: (v) => setState(() => _isPropertyOwner = v),
            ),
            SwitchListTile.adaptive(
              contentPadding: EdgeInsets.zero,
              title: const Text(
                'Es agencia aliada',
                style: TextStyle(fontSize: 14),
              ),
              value: _isAlliedAgency,
              onChanged: (v) => setState(() => _isAlliedAgency = v),
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
                  : Text(widget.isEdit ? 'Guardar cambios' : 'Crear contacto'),
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
