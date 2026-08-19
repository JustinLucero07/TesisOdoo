import '../../core/api/odoo_client.dart';

class CrmStage {
  final int id;
  final String name;
  final int sequence;
  final bool isLost;
  const CrmStage({
    required this.id,
    required this.name,
    required this.sequence,
    this.isLost = false,
  });
}

/// Trae las etapas REALES del embudo de Odoo (`crm.stage`) — el mismo
/// pipeline que se ve en el kanban del CRM web, no una lista fija copiada a
/// mano en la app.
class CrmStageService {
  final OdooClient odoo;
  CrmStageService(this.odoo);

  Future<List<CrmStage>> list() async {
    final rows = await odoo.searchRead(
      model: 'crm.stage',
      fields: ['name', 'sequence', 'is_lost'],
      order: 'sequence asc',
    );
    return rows
        .map(
          (r) => CrmStage(
            id: r['id'] as int,
            name: (r['name'] ?? '').toString(),
            sequence: r['sequence'] is num ? (r['sequence'] as num).toInt() : 0,
            isLost: r['is_lost'] == true,
          ),
        )
        .toList();
  }
}
