import '../../core/api/odoo_client.dart';
import 'contact_model.dart';

class ContactService {
  final OdooClient odoo;
  ContactService(this.odoo);

  Future<List<Contact>> list({
    String? searchText,
    String? role,
    int limit = 500,
  }) async {
    final domain = <dynamic>[];
    if (searchText != null && searchText.trim().isNotEmpty) {
      final text = searchText.trim();
      domain.addAll([
        '|',
        '|',
        '|',
        ['name', 'ilike', text],
        ['phone', 'ilike', text],
        ['mobile', 'ilike', text],
        ['email', 'ilike', text],
      ]);
    }
    switch (role) {
      case 'owner':
        domain.add(['is_property_owner', '=', true]);
      case 'agency':
        domain.add(['is_allied_agency', '=', true]);
      case 'company':
        domain.add(['is_company', '=', true]);
      case 'buyer':
        domain.add(['property_bought_count', '>', 0]);
      case 'contract':
        domain.add(['contract_count', '>', 0]);
    }
    final rows = await odoo.searchRead(
      model: 'res.partner',
      domain: domain,
      fields: Contact.listFields,
      limit: limit,
      order: 'name asc',
    );
    return rows.map(Contact.fromJson).toList();
  }

  Future<Contact> detail(int id) async {
    final rows = await odoo.searchRead(
      model: 'res.partner',
      domain: [
        ['id', '=', id],
      ],
      fields: Contact.detailFields,
      limit: 1,
    );
    return Contact.fromJson(rows.first);
  }

  Future<int> create(Map<String, dynamic> values) =>
      odoo.create(model: 'res.partner', values: values);

  Future<void> update(int id, Map<String, dynamic> values) =>
      odoo.write(model: 'res.partner', id: id, values: values);
}
