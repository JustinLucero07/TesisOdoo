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

  /// Clasificación exacta de las etapas del embudo de Postventa de Inmobi en Odoo:
  /// Seña, Financiamiento, Minuta, Transferencia de Dominio, Pago de Impuestos,
  /// Escritura, Registro Propiedad, Desembolso Banco, Encuesta, Comisión, etc.
  bool get isPostSale {
    final n = name.toLowerCase().trim();
    return n.contains('seña') ||
        n.contains('sena') ||
        n.contains('financiamiento') ||
        n.contains('minuta') ||
        n.contains('transferencia') ||
        n.contains('dominio') ||
        n.contains('impuesto') ||
        n.contains('escritura') ||
        n.contains('registro') ||
        n.contains('desembolso') ||
        n.contains('banco') ||
        n.contains('encuesta') ||
        n.contains('comisión') ||
        n.contains('comision') ||
        n.contains('posventa') ||
        n.contains('postventa') ||
        n.contains('post-venta') ||
        n.contains('entrega') ||
        n.contains('notari') ||
        n.contains('garant');
  }
}

/// Trae las etapas REALES del embudo de Odoo (`crm.stage`),
/// separando con precisión el embudo Comercial de Ventas y el de Postventa.
class CrmStageService {
  final OdooClient odoo;
  CrmStageService(this.odoo);

  Future<List<CrmStage>> list({bool? isPostSale}) async {
    final rows = await odoo.searchRead(
      model: 'crm.stage',
      fields: ['name', 'sequence', 'is_lost'],
      order: 'sequence asc',
    );
    final allStages = rows
        .map(
          (r) => CrmStage(
            id: r['id'] as int,
            name: (r['name'] ?? '').toString(),
            sequence: r['sequence'] is num ? (r['sequence'] as num).toInt() : 0,
            isLost: r['is_lost'] == true,
          ),
        )
        .toList();

    if (isPostSale == null) return allStages;

    final postStages = allStages.where((s) => s.isPostSale).toList();
    final saleStages = allStages.where((s) => !s.isPostSale).toList();

    if (isPostSale) {
      // Si Odoo tiene etapas específicas de postventa, retornarlas; si no, retornar flujo post-cierre
      if (postStages.isNotEmpty) return postStages;
      if (allStages.length > 2) {
        return allStages.sublist(allStages.length - 2);
      }
      return allStages;
    } else {
      if (postStages.isNotEmpty) return saleStages;
      return allStages;
    }
  }
}
