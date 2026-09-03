import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import 'crm_stage_service.dart';

class StageFunnel extends StatefulWidget {
  final CrmStageService service;
  final int? currentStageId;
  final ValueChanged<CrmStage> onSelect;
  final bool busy;

  const StageFunnel({
    super.key,
    required this.service,
    required this.currentStageId,
    required this.onSelect,
    this.busy = false,
  });

  @override
  State<StageFunnel> createState() => _StageFunnelState();
}

class _StageFunnelState extends State<StageFunnel> {
  List<CrmStage> _stages = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final stages = await widget.service.list();
      if (mounted) setState(() => _stages = stages);
    } catch (_) {
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.of(context);
    if (_loading) {
      return const SizedBox(
        height: 40,
        child: Center(child: LinearProgressIndicator()),
      );
    }
    if (_stages.isEmpty) return const SizedBox.shrink();

    return SizedBox(
      height: 42,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: _stages.length,
        separatorBuilder: (_, _) => const SizedBox(width: 8),
        itemBuilder: (context, i) {
          final stage = _stages[i];
          final selected = stage.id == widget.currentStageId;
          final lost = stage.isLost;
          return ChoiceChip(
            label: Text(stage.name),
            selected: selected,
            onSelected: widget.busy ? null : (_) => widget.onSelect(stage),
            selectedColor: lost ? colors.danger : colors.navy,
            backgroundColor: colors.neutralBg,
            labelStyle: TextStyle(
              color: selected
                  ? Colors.white
                  : (lost ? colors.danger : colors.ink),
              fontWeight: FontWeight.w600,
              fontSize: 12.5,
            ),
            side: BorderSide.none,
            showCheckmark: false,
          );
        },
      ),
    );
  }
}
