import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api/odoo_client.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/many2one_field.dart';
import '../../core/widgets/select_field.dart';
import '../auth/auth_service.dart';
import 'property_model.dart';
import 'property_service.dart';

/// Crea o edita una propiedad (estate.property).
///
/// A propósito NO se edita el `state` (disponible/reservada/vendida/etc.)
/// desde este formulario: marcar una propiedad como vendida en el ERP pasa
/// por el asistente de venta, que además genera la comisión, la factura y
/// despublica de WordPress — cambiar el estado a mano aquí dejaría esos
/// pasos sin hacer. Ese flujo se deja para más adelante (llamar al mismo
/// wizard desde la app), no para un campo suelto en un formulario genérico.
/// Tampoco se edita el AVM (`avm_*`) ni `days_on_market`: son calculados.
class PropertyFormScreen extends StatefulWidget {
  final Property? existing;
  const PropertyFormScreen({super.key, this.existing});

  bool get isEdit => existing != null;

  @override
  State<PropertyFormScreen> createState() => _PropertyFormScreenState();
}

class _PropertyFormScreenState extends State<PropertyFormScreen> {
  final _formKey = GlobalKey<FormState>();
  late final OdooClient _odoo;
  late final PropertyService _service;

  final _titleCtrl = TextEditingController();
  final _priceCtrl = TextEditingController();
  final _bottomPriceCtrl = TextEditingController();
  final _rentalPriceCtrl = TextEditingController();
  final _commissionCtrl = TextEditingController(text: '5.0');
  final _cityCtrl = TextEditingController();
  final _sectorCtrl = TextEditingController();
  final _streetCtrl = TextEditingController();
  final _streetNumberCtrl = TextEditingController();
  final _zipCtrl = TextEditingController();
  final _cadastralCtrl = TextEditingController();
  final _latCtrl = TextEditingController();
  final _lngCtrl = TextEditingController();
  final _areaCtrl = TextEditingController();
  final _bedroomsCtrl = TextEditingController();
  final _bathroomsCtrl = TextEditingController();
  final _parkingCtrl = TextEditingController();
  final _floorCtrl = TextEditingController();
  final _yearBuiltCtrl = TextEditingController();
  final _descriptionCtrl = TextEditingController();
  String _offerType = 'sale';
  bool _isExclusive = false;
  Many2oneValue? _propertyType;
  Many2oneValue? _owner;
  Many2oneValue? _buyer;
  Many2oneValue? _tenant;
  Many2oneValue? _advisor;

  bool _saving = false;
  String? _error;

  static const _offerOptions = [('sale', 'Venta'), ('rent', 'Arriendo')];

  @override
  void initState() {
    super.initState();
    _odoo = context.read<AuthService>().odoo;
    _service = PropertyService(_odoo);
    final p = widget.existing;
    if (p != null) {
      _titleCtrl.text = p.title;
      _priceCtrl.text = p.price > 0 ? p.price.toStringAsFixed(0) : '';
      _bottomPriceCtrl.text = p.bottomPrice > 0
          ? p.bottomPrice.toStringAsFixed(0)
          : '';
      _rentalPriceCtrl.text = p.rentalPrice > 0
          ? p.rentalPrice.toStringAsFixed(0)
          : '';
      _commissionCtrl.text = p.commissionPercentage.toStringAsFixed(1);
      _cityCtrl.text = p.city;
      _sectorCtrl.text = p.sector;
      _streetCtrl.text = p.street;
      _streetNumberCtrl.text = p.streetNumber;
      _zipCtrl.text = p.zipCode;
      _cadastralCtrl.text = p.cadastralCode;
      if (p.latitude != 0.0) _latCtrl.text = p.latitude.toString();
      if (p.longitude != 0.0) _lngCtrl.text = p.longitude.toString();
      _areaCtrl.text = p.area > 0 ? p.area.toStringAsFixed(0) : '';
      _bedroomsCtrl.text = p.bedrooms > 0 ? '${p.bedrooms}' : '';
      _bathroomsCtrl.text = p.bathrooms > 0
          ? p.bathrooms.toStringAsFixed(0)
          : '';
      _parkingCtrl.text = p.parkingSpaces > 0 ? '${p.parkingSpaces}' : '';
      _floorCtrl.text = p.floor > 0 ? '${p.floor}' : '';
      _yearBuiltCtrl.text = p.yearBuilt > 0 ? '${p.yearBuilt}' : '';
      _descriptionCtrl.text = p.description;
      _offerType = p.offerType;
      _isExclusive = p.isExclusive;
      if (p.propertyTypeId != null)
        _propertyType = Many2oneValue(p.propertyTypeId!, p.propertyTypeName);
      if (p.ownerId != null) _owner = Many2oneValue(p.ownerId!, p.ownerName);
      if (p.buyerId != null) _buyer = Many2oneValue(p.buyerId!, p.buyerName);
      if (p.tenantId != null)
        _tenant = Many2oneValue(p.tenantId!, p.tenantName);
      if (p.userId != null) _advisor = Many2oneValue(p.userId!, p.userName);
    }
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _saving = true;
      _error = null;
    });

    final vals = {
      'title': _titleCtrl.text.trim(),
      'offer_type': _offerType,
      'is_exclusive': _isExclusive,
      'price': double.tryParse(_priceCtrl.text.trim()) ?? 0.0,
      'bottom_price': double.tryParse(_bottomPriceCtrl.text.trim()) ?? 0.0,
      'rental_price': double.tryParse(_rentalPriceCtrl.text.trim()) ?? 0.0,
      'commission_percentage':
          double.tryParse(_commissionCtrl.text.trim()) ?? 5.0,
      'city': _cityCtrl.text.trim(),
      'sector': _sectorCtrl.text.trim(),
      'street': _streetCtrl.text.trim(),
      'street_number': _streetNumberCtrl.text.trim(),
      'zip_code': _zipCtrl.text.trim(),
      'cadastral_code': _cadastralCtrl.text.trim(),
      'latitude': double.tryParse(_latCtrl.text.trim()) ?? 0.0,
      'longitude': double.tryParse(_lngCtrl.text.trim()) ?? 0.0,
      'area': double.tryParse(_areaCtrl.text.trim()) ?? 0.0,
      'bedrooms': int.tryParse(_bedroomsCtrl.text.trim()) ?? 0,
      'bathrooms': double.tryParse(_bathroomsCtrl.text.trim()) ?? 0.0,
      'parking_spaces': int.tryParse(_parkingCtrl.text.trim()) ?? 0,
      'floor': int.tryParse(_floorCtrl.text.trim()) ?? 0,
      'year_built': int.tryParse(_yearBuiltCtrl.text.trim()) ?? 0,
      'description': _descriptionCtrl.text.trim(),
      if (_propertyType != null) 'property_type_id': _propertyType!.id,
      'owner_id': _owner?.id ?? false,
      'buyer_id': _buyer?.id ?? false,
      'tenant_id': _tenant?.id ?? false,
      if (_advisor != null) 'user_id': _advisor!.id,
      if (!widget.isEdit) 'state': 'available',
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
        () => _error = 'No se pudo guardar la propiedad. Intenta de nuevo.',
      );
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.isEdit ? 'Editar propiedad' : 'Nueva propiedad'),
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(18),
          children: [
            TextFormField(
              controller: _titleCtrl,
              decoration: const InputDecoration(labelText: 'Título *'),
              validator: (v) =>
                  (v == null || v.trim().isEmpty) ? 'Requerido' : null,
            ),
            const SizedBox(height: 14),
            Many2oneField(
              label: 'Tipo de propiedad',
              odoo: _odoo,
              model: 'estate.property.type',
              value: _propertyType,
              onChanged: (v) => setState(() => _propertyType = v),
            ),
            const SizedBox(height: 14),
            SelectField(
              label: 'Operación',
              value: _offerType,
              options: _offerOptions,
              onChanged: (v) => setState(() => _offerType = v ?? 'sale'),
            ),
            const SizedBox(height: 4),
            SwitchListTile.adaptive(
              contentPadding: EdgeInsets.zero,
              title: const Text(
                'Propiedad exclusiva',
                style: TextStyle(fontSize: 14),
              ),
              value: _isExclusive,
              onChanged: (v) => setState(() => _isExclusive = v),
            ),
            const _FormSectionTitle('Precio y comisión'),
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: _priceCtrl,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Precio de venta (\$)',
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextFormField(
                    controller: _rentalPriceCtrl,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Precio de arriendo (\$)',
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
                    controller: _bottomPriceCtrl,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Precio tope (mínimo)',
                    ),
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
            const _FormSectionTitle('Ubicación'),
            TextFormField(
              controller: _cityCtrl,
              decoration: const InputDecoration(labelText: 'Ciudad'),
            ),
            const SizedBox(height: 14),
            TextFormField(
              controller: _sectorCtrl,
              decoration: const InputDecoration(labelText: 'Sector / Barrio'),
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  flex: 3,
                  child: TextFormField(
                    controller: _streetCtrl,
                    decoration: const InputDecoration(labelText: 'Dirección'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextFormField(
                    controller: _streetNumberCtrl,
                    decoration: const InputDecoration(labelText: 'N°'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: _zipCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Código postal',
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextFormField(
                    controller: _cadastralCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Clave catastral',
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
                    controller: _latCtrl,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                      signed: true,
                    ),
                    decoration: const InputDecoration(
                      labelText: 'Latitud GPS',
                      hintText: 'Ej: -2.8974',
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextFormField(
                    controller: _lngCtrl,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                      signed: true,
                    ),
                    decoration: const InputDecoration(
                      labelText: 'Longitud GPS',
                      hintText: 'Ej: -79.0045',
                    ),
                  ),
                ),
              ],
            ),
            const _FormSectionTitle('Características'),
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: _areaCtrl,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: 'Área (m²)'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextFormField(
                    controller: _bedroomsCtrl,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Habitaciones',
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextFormField(
                    controller: _bathroomsCtrl,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: 'Baños'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: _parkingCtrl,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Parqueaderos',
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextFormField(
                    controller: _floorCtrl,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: 'Piso'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextFormField(
                    controller: _yearBuiltCtrl,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Año construcción',
                    ),
                  ),
                ),
              ],
            ),
            const _FormSectionTitle('Personas relacionadas'),
            Many2oneField(
              label: 'Propietario',
              odoo: _odoo,
              model: 'res.partner',
              value: _owner,
              onChanged: (v) => setState(() => _owner = v),
            ),
            const SizedBox(height: 14),
            Many2oneField(
              label: 'Comprador',
              odoo: _odoo,
              model: 'res.partner',
              value: _buyer,
              onChanged: (v) => setState(() => _buyer = v),
            ),
            const SizedBox(height: 14),
            Many2oneField(
              label: 'Arrendatario',
              odoo: _odoo,
              model: 'res.partner',
              value: _tenant,
              onChanged: (v) => setState(() => _tenant = v),
            ),
            const SizedBox(height: 14),
            Many2oneField(
              label: 'Asesor responsable',
              odoo: _odoo,
              model: 'res.users',
              value: _advisor,
              onChanged: (v) => setState(() => _advisor = v),
            ),
            const _FormSectionTitle('Descripción'),
            TextFormField(
              controller: _descriptionCtrl,
              minLines: 3,
              maxLines: 6,
              decoration: const InputDecoration(alignLabelWithHint: true),
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
                  : Text(widget.isEdit ? 'Guardar cambios' : 'Crear propiedad'),
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
