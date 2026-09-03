import '../../core/api/odoo_client.dart';
import 'offer_model.dart';

class OfferService {
  final OdooClient odoo;
  OfferService(this.odoo);

  Future<List<Offer>> list({
    String? state,
    int? propertyId,
    int? leadId,
    int limit = 80,
  }) async {
    final domain = <dynamic>[];
    if (state != null) domain.add(['state', '=', state]);
    if (propertyId != null) domain.add(['property_id', '=', propertyId]);
    if (leadId != null) domain.add(['lead_id', '=', leadId]);
    final rows = await odoo.searchRead(
      model: 'estate.property.offer',
      domain: domain,
      fields: Offer.fields,
      limit: limit,
      order: 'date desc, id desc',
    );
    return rows.map(Offer.fromJson).toList();
  }

  Future<int> create(Map<String, dynamic> values) =>
      odoo.create(model: 'estate.property.offer', values: values);

  Future<void> update(int id, Map<String, dynamic> values) =>
      odoo.write(model: 'estate.property.offer', id: id, values: values);

  Future<void> runAction(int id, String method) => odoo.callKw(
    model: 'estate.property.offer',
    method: method,
    args: [
      [id],
    ],
  );
}
