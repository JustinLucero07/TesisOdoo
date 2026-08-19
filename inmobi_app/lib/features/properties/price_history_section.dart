import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/api/odoo_client.dart';
import '../../core/theme/app_theme.dart';
import '../finance/finance_models.dart';

/// Historial de cambios de precio de una propiedad
/// (`estate.property.price.history`) — muestra si el precio subió o bajó y
/// en qué proporción, que es lo que un asesor necesita para argumentar.
class PriceHistorySection extends StatefulWidget {
  final OdooClient odoo;
  final int propertyId;
  const PriceHistorySection({
    super.key,
    required this.odoo,
    required this.propertyId,
  });

  @override
  State<PriceHistorySection> createState() => _PriceHistorySectionState();
}

class _PriceHistorySectionState extends State<PriceHistorySection> {
  List<PriceChange> _items = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final rows = await widget.odoo.searchRead(
        model: 'estate.property.price.history',
        domain: [
          ['property_id', '=', widget.propertyId],
        ],
        fields: PriceChange.fields,
        order: 'date desc',
        limit: 20,
      );
      if (mounted)
        setState(() => _items = rows.map(PriceChange.fromJson).toList());
    } catch (_) {
      // Silencioso: la sección queda vacía si falla.
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = AppColors.of(context);
    final currency = NumberFormat.currency(
      locale: 'es_EC',
      symbol: '\$',
      decimalDigits: 0,
    );
    final dateFmt = DateFormat('d MMM y', 'es_EC');

    if (_loading) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: AppSpace.md),
        child: LinearProgressIndicator(),
      );
    }
    if (_items.isEmpty) {
      return Text(
        'El precio no ha cambiado desde la publicación.',
        style: AppType.bodySmall.copyWith(color: p.mutedLight),
      );
    }

    return Column(
      children: [
        for (int i = 0; i < _items.length; i++) ...[
          if (i > 0) Divider(height: 1, color: p.line),
          Padding(
            padding: const EdgeInsets.symmetric(vertical: AppSpace.md),
            child: Row(
              children: [
                Container(
                  width: 30,
                  height: 30,
                  decoration: BoxDecoration(
                    color: (_items[i].isDrop ? p.danger : p.success).withValues(
                      alpha: 0.12,
                    ),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    _items[i].isDrop ? Icons.trending_down : Icons.trending_up,
                    size: 16,
                    color: _items[i].isDrop ? p.danger : p.success,
                  ),
                ),
                const SizedBox(width: AppSpace.md),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${currency.format(_items[i].oldPrice)} → ${currency.format(_items[i].newPrice)}',
                        style: AppType.bodySmall.copyWith(
                          fontWeight: FontWeight.w600,
                          color: p.ink,
                        ),
                      ),
                      if (_items[i].date != null)
                        Text(
                          dateFmt.format(_items[i].date!),
                          style: AppType.caption.copyWith(color: p.mutedLight),
                        ),
                    ],
                  ),
                ),
                Text(
                  '${_items[i].changePct > 0 ? '+' : ''}${_items[i].changePct.toStringAsFixed(1)}%',
                  style: AppType.bodySmall.copyWith(
                    fontWeight: FontWeight.w600,
                    color: _items[i].isDrop ? p.danger : p.success,
                  ),
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }
}
