import '../../core/api/odoo_client.dart';
import 'property_model.dart';

/// Consulta propiedades reales de `estate.property` vía ORM (search_read),
/// respetando los permisos del usuario logueado — el mismo dato que vería
/// en el ERP, sin ningún endpoint nuevo.
class PropertyService {
  final OdooClient odoo;
  PropertyService(this.odoo);

  Future<List<Property>> list({
    String? searchText,
    List<String>? states,
    String? offerType,
    int limit = 40,
    int offset = 0,
  }) async {
    final domain = <dynamic>[];
    if (searchText != null && searchText.trim().isNotEmpty) {
      final text = searchText.trim();
      domain.addAll([
        '|',
        '|',
        ['title', 'ilike', text],
        ['city', 'ilike', text],
        ['sector', 'ilike', text],
      ]);
    }
    if (states != null && states.isNotEmpty) {
      domain.add(['state', 'in', states]);
    }
    if (offerType != null) {
      domain.add(['offer_type', '=', offerType]);
    }
    final rows = await odoo.searchRead(
      model: 'estate.property',
      domain: domain,
      fields: Property.listFields,
      limit: limit,
      offset: offset,
      order: 'create_date desc',
    );
    return rows.map(Property.fromJson).toList();
  }

  Future<Property> detail(int id) async {
    final rows = await odoo.searchRead(
      model: 'estate.property',
      domain: [
        ['id', '=', id],
      ],
      fields: Property.detailFields,
      limit: 1,
    );
    return Property.fromJson(rows.first);
  }

  Future<int> create(Map<String, dynamic> values) =>
      odoo.create(model: 'estate.property', values: values);

  Future<void> update(int id, Map<String, dynamic> values) =>
      odoo.write(model: 'estate.property', id: id, values: values);
}
