import '../../core/api/odoo_client.dart';
import 'lead_model.dart';

class LeadService {
  final OdooClient odoo;
  LeadService(this.odoo);

  Future<List<Lead>> list({
    String? searchText,
    String? temperature,
    int? stageId,
    int limit = 40,
  }) async {
    final domain = <dynamic>[
      ['type', '=', 'opportunity'],
      ['active', '=', true],
    ];
    if (searchText != null && searchText.trim().isNotEmpty) {
      final text = searchText.trim();
      domain.addAll([
        '|',
        ['name', 'ilike', text],
        ['contact_name', 'ilike', text],
      ]);
    }
    if (temperature != null) {
      domain.add(['lead_temperature', '=', temperature]);
    }
    if (stageId != null) {
      domain.add(['stage_id', '=', stageId]);
    }
    final rows = await odoo.searchRead(
      model: 'crm.lead',
      domain: domain,
      fields: Lead.listFields,
      limit: limit,
      order: 'lead_temperature desc, write_date desc',
    );
    return rows.map(Lead.fromJson).toList();
  }

  Future<int> countHot() async {
    final result = await odoo.callKw(
      model: 'crm.lead',
      method: 'search_count',
      args: [
        [
          ['type', '=', 'opportunity'],
          ['active', '=', true],
          [
            'lead_temperature',
            'in',
            ['hot', 'boiling'],
          ],
        ],
      ],
    );
    return result as int;
  }

  /// Crea una oportunidad nueva — `type: 'opportunity'` es obligatorio para
  /// que aparezca en el listado (que solo trae oportunidades, no leads sin
  /// calificar).
  Future<int> create(Map<String, dynamic> values) => odoo.create(
    model: 'crm.lead',
    values: {'type': 'opportunity', ...values},
  );

  Future<void> update(int id, Map<String, dynamic> values) =>
      odoo.write(model: 'crm.lead', id: id, values: values);
}
