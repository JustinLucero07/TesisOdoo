import '../../core/api/odoo_client.dart';
import 'lead_model.dart';

class LeadService {
  final OdooClient odoo;
  LeadService(this.odoo);

  Future<List<Lead>> list({
    String? searchText,
    String? temperature,
    int? stageId,
    List<int>? stageIds,
    bool myLeadsOnly = false,
    int? currentUserId,
    int? advisorId,
    double? minBudget,
    double? maxBudget,
    int? priority,
    String order = 'lead_temperature desc, write_date desc',
    int limit = 50,
    int offset = 0,
  }) async {
    final rows = await odoo.searchRead(
      model: 'crm.lead',
      domain: _domain(
        searchText: searchText,
        temperature: temperature,
        stageId: stageId,
        stageIds: stageIds,
        myLeadsOnly: myLeadsOnly,
        currentUserId: currentUserId,
        advisorId: advisorId,
        minBudget: minBudget,
        maxBudget: maxBudget,
        priority: priority,
      ),
      fields: Lead.listFields,
      limit: limit,
      offset: offset > 0 ? offset : null,
      order: order,
    );
    return rows.map(Lead.fromJson).toList();
  }

  /// Cuántos leads hay con los mismos filtros (para el contador de cada
  /// columna del embudo, que carga de a poco).
  Future<int> count({
    String? searchText,
    int? stageId,
    bool myLeadsOnly = false,
    int? currentUserId,
    int? advisorId,
  }) async {
    final result = await odoo.callKw(
      model: 'crm.lead',
      method: 'search_count',
      args: [
        _domain(
          searchText: searchText,
          stageId: stageId,
          myLeadsOnly: myLeadsOnly,
          currentUserId: currentUserId,
          advisorId: advisorId,
        ),
      ],
    );
    return result as int;
  }

  List<dynamic> _domain({
    String? searchText,
    String? temperature,
    int? stageId,
    List<int>? stageIds,
    bool myLeadsOnly = false,
    int? currentUserId,
    int? advisorId,
    double? minBudget,
    double? maxBudget,
    int? priority,
  }) {
    final domain = <dynamic>[
      ['type', '=', 'opportunity'],
      ['active', '=', true],
    ];
    if (searchText != null && searchText.trim().isNotEmpty) {
      final text = searchText.trim();
      // Se busca en todo lo que el asesor puede tener a mano: el título del
      // lead, el contacto (escrito o vinculado), el asesor y el teléfono.
      domain.addAll([
        '|',
        '|',
        '|',
        '|',
        ['name', 'ilike', text],
        ['contact_name', 'ilike', text],
        ['partner_id.name', 'ilike', text],
        ['user_id.name', 'ilike', text],
        ['phone', 'ilike', text],
      ]);
    }
    if (temperature != null) {
      domain.add(['lead_temperature', '=', temperature]);
    }
    if (stageId != null) {
      domain.add(['stage_id', '=', stageId]);
    }
    // Restringir al embudo en el servidor y no después en el celular: el
    // `limit` se aplica antes de descartar, así que filtrar acá evita que
    // los 50 primeros se llenen con leads del otro embudo y la lista salga
    // vacía (pasaba al elegir "Todos los asesores").
    if (stageIds != null && stageIds.isNotEmpty) {
      domain.add(['stage_id', 'in', stageIds]);
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
    return domain;
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
