import '../../core/api/odoo_client.dart';
import 'contract_model.dart';

class ContractService {
  final OdooClient odoo;
  ContractService(this.odoo);

  Future<List<Contract>> list({
    String? searchText,
    int? propertyId,
    String? state,
    int limit = 40,
  }) async {
    final domain = <dynamic>[];
    if (searchText != null && searchText.trim().isNotEmpty) {
      domain.add(['name', 'ilike', searchText.trim()]);
    }
    if (propertyId != null) {
      domain.add(['property_id', '=', propertyId]);
    }
    if (state != null) {
      domain.add(['state', '=', state]);
    }
    final rows = await odoo.searchRead(
      model: 'estate.contract',
      domain: domain,
      fields: Contract.listFields,
      limit: limit,
      order: 'date_start desc',
    );
    return rows.map(Contract.fromJson).toList();
  }

  Future<Contract> detail(int id) async {
    final rows = await odoo.searchRead(
      model: 'estate.contract',
      domain: [
        ['id', '=', id],
      ],
      fields: Contract.listFields,
      limit: 1,
    );
    return Contract.fromJson(rows.first);
  }

  Future<int> create(Map<String, dynamic> values) =>
      odoo.create(model: 'estate.contract', values: values);

  Future<void> update(int id, Map<String, dynamic> values) =>
      odoo.write(model: 'estate.contract', id: id, values: values);
}
