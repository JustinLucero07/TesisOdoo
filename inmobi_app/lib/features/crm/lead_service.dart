import '../../core/api/odoo_client.dart';
import 'lead_model.dart';

class LeadService {
  final OdooClient odoo;
  LeadService(this.odoo);

  Future<List<Lead>> list({
    String? searchText,
    String? temperature,
    int? stageId,
    bool myLeadsOnly = false,
    int? currentUserId,
    int? advisorId,
    double? minBudget,
    double? maxBudget,
    int? priority,
    String order = 'lead_temperature desc, write_date desc',
    int limit = 50,
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
    if (advisorId != null) {
      domain.add(['user_id', '=', advisorId]);
    } else if (myLeadsOnly && currentUserId != null) {
      domain.add(['user_id', '=', currentUserId]);
    }
    if (minBudget != null && minBudget > 0) {
      domain.add(['client_budget', '>=', minBudget]);
    }
    if (maxBudget != null && maxBudget > 0) {
      domain.add(['client_budget', '<=', maxBudget]);
    }
    if (priority != null && priority > 0) {
      domain.add(['priority', '>=', priority.toString()]);
    }

    final rows = await odoo.searchRead(
      model: 'crm.lead',
      domain: domain,
      fields: Lead.listFields,
      limit: limit,
      order: order,
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

  Future<int> create(Map<String, dynamic> values) => odoo.create(
    model: 'crm.lead',
    values: {'type': 'opportunity', ...values},
  );

  Future<void> update(int id, Map<String, dynamic> values) =>
      odoo.write(model: 'crm.lead', id: id, values: values);
}
