import '../../core/api/odoo_client.dart';
import 'document_model.dart';

/// Relación a la que pertenecen los documentos consultados/creados — solo una
/// debe tener valor a la vez (mismo modelo `estate.document` que usa el ERP
/// para propiedades, leads, contratos y contactos).
class DocumentOwner {
  final String field;
  final int id;
  const DocumentOwner.property(this.id) : field = 'property_id';
  const DocumentOwner.lead(this.id) : field = 'lead_id';
  const DocumentOwner.contract(this.id) : field = 'contract_id';
  const DocumentOwner.partner(this.id) : field = 'partner_id';
}

class DocumentService {
  final OdooClient odoo;
  DocumentService(this.odoo);

  Future<List<EstateDocument>> list(DocumentOwner owner) async {
    final rows = await odoo.searchRead(
      model: 'estate.document',
      domain: [
        [owner.field, '=', owner.id],
      ],
      fields: EstateDocument.listFields,
      order: 'date desc',
    );
    return rows.map(EstateDocument.fromJson).toList();
  }

  Future<int> upload({
    required DocumentOwner owner,
    required String name,
    required String filename,
    required String base64File,
    required int typeId,
  }) {
    return odoo.create(
      model: 'estate.document',
      values: {
        owner.field: owner.id,
        'name': name,
        'filename': filename,
        'file': base64File,
        'type_id': typeId,
        'state': 'received',
      },
    );
  }
}
