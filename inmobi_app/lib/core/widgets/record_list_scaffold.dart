import 'package:flutter/material.dart';

import '../theme/app_theme.dart';
import 'choice_chip_row.dart';
import 'motion.dart';
import 'skeleton.dart';
import 'states.dart';

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

  /// Si se indica, la lista se parte en secciones con este título. El orden de
  /// llegada manda: los elementos ya vienen ordenados desde el servidor.
  final String Function(T item)? groupBy;

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
    this.groupBy,
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
    const padding = EdgeInsets.fromLTRB(
      AppSpace.lg,
      AppSpace.xs,
      AppSpace.lg,
      90,
    );

    final agrupar = widget.groupBy;
    if (agrupar == null) {
      return ListView.separated(
        padding: padding,
        itemCount: _items.length,
        separatorBuilder: (_, _) => const SizedBox(height: 10),
        itemBuilder: (context, i) => FadeSlideIn(
          index: i,
          child: widget.itemBuilder(context, _items[i]),
        ),
      );
    }

    // Cada elemento va precedido de su cabecera cuando cambia el grupo.
    final filas = <Widget>[];
    String? grupoActual;
    for (var i = 0; i < _items.length; i++) {
      final grupo = agrupar(_items[i]);
      if (grupo != grupoActual) {
        grupoActual = grupo;
        filas.add(_GroupHeader(title: grupo.isEmpty ? 'Sin asignar' : grupo));
      }
      filas.add(
        FadeSlideIn(index: i, child: widget.itemBuilder(context, _items[i])),
      );
    }
    return ListView.separated(
      padding: padding,
      itemCount: filas.length,
      separatorBuilder: (_, _) => const SizedBox(height: 10),
      itemBuilder: (context, i) => filas[i],
    );
  }
}

class _GroupHeader extends StatelessWidget {
  final String title;
  const _GroupHeader({required this.title});

  @override
  Widget build(BuildContext context) {
    final p = AppColors.of(context);
    return Padding(
      padding: const EdgeInsets.only(top: 6, bottom: 2),
      child: Row(
        children: [
          Text(
            title.toUpperCase(),
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w800,
              letterSpacing: 0.8,
              color: p.muted,
            ),
          ),
          const SizedBox(width: 10),
          Expanded(child: Divider(color: p.line, height: 1)),
        ],
      ),
    );
  }
}

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
