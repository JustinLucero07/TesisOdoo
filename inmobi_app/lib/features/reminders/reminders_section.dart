import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/api/odoo_client.dart';
import '../../core/theme/app_theme.dart';
import 'reminder_form_screen.dart';
import 'reminder_model.dart';
import 'reminder_service.dart';

/// Bloque de recordatorios que se incrusta en la ficha de un cliente.
class RemindersSection extends StatefulWidget {
  final OdooClient odoo;
  final int partnerId;
  final String partnerName;

  const RemindersSection({
    super.key,
    required this.odoo,
    required this.partnerId,
    required this.partnerName,
  });

  @override
  State<RemindersSection> createState() => _RemindersSectionState();
}

class _RemindersSectionState extends State<RemindersSection> {
  late final ReminderService _service;
  List<Reminder> _items = [];
  bool _loading = true;
  bool _showDone = false;

  @override
  void initState() {
    super.initState();
    _service = ReminderService(widget.odoo);
    _load();
  }

  @override
  void didUpdateWidget(covariant RemindersSection oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.partnerId != widget.partnerId) _load();
  }

  Future<void> _reprogramar() => ReminderService.scheduleAllUpcoming(
    widget.odoo,
    currentUserId: widget.odoo.userId,
  );

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final items = await _service.list(
        partnerId: widget.partnerId,
        filter: _showDone ? null : 'pending',
      );
      if (mounted) setState(() => _items = items);
    } catch (_) {
      if (mounted) setState(() => _items = []);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _openForm({Reminder? existing}) async {
    final saved = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => ReminderFormScreen(
          existing: existing,
          initialPartnerId: widget.partnerId,
          initialPartnerName: widget.partnerName,
        ),
      ),
    );
    if (saved == true && mounted) _load();
  }

  Future<void> _toggleDone(Reminder r) async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      if (r.isPending) {
        await _service.markDone(r.id);
      } else {
        await _service.reopen(r.id);
      }
      await _reprogramar();
      await _load();
    } catch (_) {
      messenger.showSnackBar(
        const SnackBar(content: Text('No se pudo actualizar el recordatorio.')),
      );
    }
  }

  Future<void> _delete(Reminder r) async {
    final messenger = ScaffoldMessenger.of(context);
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Eliminar recordatorio'),
        content: Text('¿Eliminar "${r.name}"? No se puede deshacer.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Eliminar'),
          ),
        ],
      ),
    );
    if (confirm != true) return;
    try {
      await _service.delete(r.id);
      await _reprogramar();
      await _load();
    } catch (_) {
      messenger.showSnackBar(
        const SnackBar(content: Text('No se pudo eliminar el recordatorio.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colors = AppColors.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(
              'Recordatorios (${_items.length})',
              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
            ),
            const Spacer(),
            if (_items.isNotEmpty || _showDone)
              IconButton(
                tooltip: _showDone ? 'Ver solo pendientes' : 'Ver todos',
                visualDensity: VisualDensity.compact,
                onPressed: () {
                  setState(() => _showDone = !_showDone);
                  _load();
                },
                icon: Icon(
                  _showDone ? Icons.filter_alt_off_outlined : Icons.history,
                  size: 19,
                ),
              ),
            FilledButton.icon(
              style: FilledButton.styleFrom(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 6,
                ),
                visualDensity: VisualDensity.compact,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
              onPressed: () => _openForm(),
              icon: const Icon(Icons.add_alert_rounded, size: 16),
              label: const Text('Añadir', style: TextStyle(fontSize: 12.5)),
            ),
          ],
        ),
        const SizedBox(height: 8),
        if (_loading)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 12),
            child: LinearProgressIndicator(),
          )
        else if (_items.isEmpty)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 16),
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF1E1A3E) : colors.neutralBg,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: isDark ? Colors.white12 : colors.line),
            ),
            child: Column(
              children: [
                Icon(
                  Icons.notifications_none_rounded,
                  size: 36,
                  color: colors.mutedLight,
                ),
                const SizedBox(height: 6),
                Text(
                  'Sin recordatorios para este cliente.',
                  style: TextStyle(
                    fontSize: 13,
                    color: colors.muted,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Pólizas, cuotas o renovaciones: te avisamos antes.',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 11.5, color: colors.mutedLight),
                ),
                const SizedBox(height: 10),
                OutlinedButton.icon(
                  onPressed: () => _openForm(),
                  icon: const Icon(Icons.add_alert_outlined, size: 16),
                  label: const Text(
                    'Crear recordatorio',
                    style: TextStyle(fontSize: 12.5),
                  ),
                ),
              ],
            ),
          )
        else
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: _items.length,
            separatorBuilder: (_, _) => const SizedBox(height: 10),
            itemBuilder: (context, i) => ReminderTile(
              reminder: _items[i],
              showPartner: false,
              onTap: () => _openForm(existing: _items[i]),
              onToggleDone: () => _toggleDone(_items[i]),
              onDelete: () => _delete(_items[i]),
            ),
          ),
      ],
    );
  }
}

/// Tarjeta de un recordatorio, compartida por la ficha del cliente y la lista.
class ReminderTile extends StatelessWidget {
  final Reminder reminder;
  final bool showPartner;
  final VoidCallback onTap;
  final VoidCallback onToggleDone;
  final VoidCallback? onDelete;

  const ReminderTile({
    super.key,
    required this.reminder,
    required this.onTap,
    required this.onToggleDone,
    this.showPartner = true,
    this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colors = AppColors.of(context);
    final dateFmt = DateFormat('d MMM y', 'es_EC');
    final r = reminder;
    final urgency = ReminderStateStyle.urgencyColor(r, colors);

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(14),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF1E1A3E) : Colors.white,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: r.isOverdue
                ? colors.danger.withValues(alpha: 0.45)
                : (isDark ? Colors.white12 : colors.line),
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: urgency.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(11),
              ),
              child: Icon(
                ReminderTypeStyle.icon(r.reminderType),
                size: 20,
                color: urgency,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    r.name,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 13.5,
                      decoration: r.state == 'done'
                          ? TextDecoration.lineThrough
                          : null,
                      color: r.state == 'done' ? colors.muted : null,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    [
                      if (showPartner && r.partnerName.isNotEmpty)
                        r.partnerName,
                      if (r.date != null)
                        '${dateFmt.format(r.date!)} · ${r.hourLabel}',
                      if (r.documentName.isNotEmpty)
                        '📎 ${r.documentName}'
                      else
                        ReminderTypeStyle.label(r.reminderType),
                    ].join(' · '),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 11.5, color: colors.muted),
                  ),
                  const SizedBox(height: 5),
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: urgency.withValues(alpha: 0.13),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          r.countdownLabel,
                          style: TextStyle(
                            fontSize: 10.5,
                            fontWeight: FontWeight.w800,
                            color: urgency,
                          ),
                        ),
                      ),
                      if (r.isPending && !r.advanceNotified) ...[
                        const SizedBox(width: 6),
                        Text(
                          r.remindLabel,
                          style: TextStyle(
                            fontSize: 10,
                            color: colors.mutedLight,
                          ),
                        ),
                      ],
                      if (r.isPending && r.advanceNotified) ...[
                        const SizedBox(width: 6),
                        Icon(
                          Icons.notifications_active_rounded,
                          size: 13,
                          color: colors.mutedLight,
                        ),
                      ],
                    ],
                  ),
                ],
              ),
            ),
            IconButton(
              tooltip: r.isPending ? 'Marcar como hecho' : 'Reabrir',
              visualDensity: VisualDensity.compact,
              onPressed: onToggleDone,
              icon: Icon(
                r.isPending
                    ? Icons.check_circle_outline_rounded
                    : Icons.replay_rounded,
                size: 21,
                color: r.isPending ? colors.success : colors.muted,
              ),
            ),
            if (onDelete != null)
              IconButton(
                tooltip: 'Eliminar',
                visualDensity: VisualDensity.compact,
                onPressed: onDelete,
                icon: Icon(
                  Icons.delete_outline_rounded,
                  size: 20,
                  color: colors.mutedLight,
                ),
              ),
          ],
        ),
      ),
    );
  }
}
