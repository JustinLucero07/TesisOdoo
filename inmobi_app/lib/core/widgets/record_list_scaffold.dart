import 'package:flutter/material.dart';

import '../theme/app_theme.dart';
import 'choice_chip_row.dart';
import 'motion.dart';
import 'skeleton.dart';
import 'states.dart';

/// Andamio común de las pantallas de listado (ofertas, comisiones, pagos,
/// gastos, tasaciones). Concentra el patrón que ya se repetía pantalla a
/// pantalla: cargar, filtrar por estado, refrescar, y los tres estados de
/// salida (cargando / error / vacío).
class RecordListScaffold<T> extends StatefulWidget {
  final String title;
  final Future<List<T>> Function(String? filter) load;
  final Widget Function(BuildContext context, T item) itemBuilder;
  final List<(String?, String)>? filters;
  final String emptyMessage;
  final IconData emptyIcon;
  final String errorMessage;
  final Widget? Function(List<T> items)? summaryBuilder;
  final VoidCallback? onCreate;
  final String? createLabel;

  const RecordListScaffold({
    super.key,
    required this.title,
    required this.load,
    required this.itemBuilder,
    this.filters,
    required this.emptyMessage,
    this.emptyIcon = Icons.inbox_outlined,
    required this.errorMessage,
    this.summaryBuilder,
    this.onCreate,
    this.createLabel,
  });

  @override
  State<RecordListScaffold<T>> createState() => _RecordListScaffoldState<T>();
}

class _RecordListScaffoldState<T> extends State<RecordListScaffold<T>> {
  List<T> _items = [];
  bool _loading = true;
  String? _error;
  String? _filter;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final result = await widget.load(_filter);
      if (mounted) setState(() => _items = result);
    } catch (e) {
      if (mounted) setState(() => _error = widget.errorMessage);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _create() async {
    widget.onCreate?.call();
  }

  @override
  Widget build(BuildContext context) {
    final p = AppColors.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(widget.title)),
      floatingActionButton: widget.onCreate == null
          ? null
          : FloatingActionButton.extended(
              heroTag: null,
              onPressed: _create,
              icon: const Icon(Icons.add),
              label: Text(widget.createLabel ?? 'Nuevo'),
            ),
      body: Column(
        children: [
          if (widget.filters != null) ...[
            const SizedBox(height: AppSpace.md),
            ChoiceChipRow(
              options: widget.filters!,
              value: _filter,
              onChanged: (v) {
                setState(() => _filter = v);
                _load();
              },
            ),
          ],
          if (!_loading && _error == null && widget.summaryBuilder != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(
                AppSpace.lg,
                AppSpace.md,
                AppSpace.lg,
                0,
              ),
              child: widget.summaryBuilder!(_items) ?? const SizedBox.shrink(),
            ),
          const SizedBox(height: AppSpace.sm),
          Expanded(
            child: RefreshIndicator(
              onRefresh: _load,
              color: p.navy,
              child: _buildBody(),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_loading) return const SkeletonList();
    if (_error != null) {
      return MessageView(
        icon: Icons.error_outline,
        message: _error!,
        onRetry: _load,
      );
    }
    if (_items.isEmpty) {
      return ListView(
        children: [
          const SizedBox(height: 60),
          MessageView(icon: widget.emptyIcon, message: widget.emptyMessage),
        ],
      );
    }
    return ListView.separated(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.lg,
        AppSpace.xs,
        AppSpace.lg,
        90,
      ),
      itemCount: _items.length,
      separatorBuilder: (_, _) => const SizedBox(height: 10),
      // La lista se arma sola: cada fila entra un instante después de la
      // anterior. Como este andamio lo usan Ofertas, Comisiones, Pagos,
      // Gastos y Tasaciones, todas ganan el mismo comportamiento de una.
      itemBuilder: (context, i) => FadeSlideIn(
        index: i,
        child: widget.itemBuilder(context, _items[i]),
      ),
    );
  }
}

/// Banda de totales que va sobre una lista (suma de comisiones, de pagos…).
class TotalsBar extends StatelessWidget {
  final List<(String, String)> entries;
  const TotalsBar({super.key, required this.entries});

  @override
  Widget build(BuildContext context) {
    final p = AppColors.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpace.lg,
        vertical: AppSpace.md,
      ),
      decoration: BoxDecoration(
        color: p.surfaceAlt,
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
      child: Row(
        children: [
          for (int i = 0; i < entries.length; i++) ...[
            if (i > 0) Container(width: 1, height: 30, color: p.line),
            Expanded(
              child: Padding(
                padding: EdgeInsets.only(left: i > 0 ? AppSpace.md : 0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      entries[i].$1,
                      style: AppType.caption.copyWith(color: p.mutedLight),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      entries[i].$2,
                      style: AppType.heading.copyWith(color: p.navy),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
