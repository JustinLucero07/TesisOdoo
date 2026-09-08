import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/widgets/record_list_scaffold.dart';
import '../auth/auth_service.dart';
import 'reminder_form_screen.dart';
import 'reminder_model.dart';
import 'reminder_service.dart';
import 'reminders_section.dart';

class ReminderListScreen extends StatefulWidget {
  const ReminderListScreen({super.key});

  @override
  State<ReminderListScreen> createState() => _ReminderListScreenState();
}

class _ReminderListScreenState extends State<ReminderListScreen> {
  int _version = 0;

  void _refresh() => setState(() => _version++);

  Future<void> _create() async {
    final saved = await Navigator.of(
      context,
    ).push<bool>(MaterialPageRoute(builder: (_) => const ReminderFormScreen()));
    if (saved == true) _refresh();
  }

  Future<void> _edit(Reminder r) async {
    final saved = await Navigator.of(context).push<bool>(
      MaterialPageRoute(builder: (_) => ReminderFormScreen(existing: r)),
    );
    if (saved == true) _refresh();
  }

  Future<void> _toggleDone(ReminderService service, Reminder r) async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      if (r.isPending) {
        await service.markDone(r.id);
      } else {
        await service.reopen(r.id);
      }
      _refresh();
    } catch (_) {
      messenger.showSnackBar(
        const SnackBar(content: Text('No se pudo actualizar el recordatorio.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final odoo = context.read<AuthService>().odoo;
    final service = ReminderService(odoo);

    return RecordListScaffold<Reminder>(
      key: ValueKey(_version),
      title: 'Recordatorios',
      errorMessage: 'No se pudieron cargar los recordatorios.',
      emptyMessage: 'No tienes recordatorios en este filtro.',
      emptyIcon: Icons.notifications_none_rounded,
      onCreate: _create,
      createLabel: 'Recordatorio',
      filters: const [
        ('pending', 'Pendientes'),
        ('soon', 'Por avisar'),
        ('overdue', 'Vencidos'),
        ('done', 'Hechos'),
        (null, 'Todos'),
      ],
      // Un asesor ve los recordatorios de los que es responsable; el admin,
      // los de toda la oficina.
      load: (filter) => service.list(
        filter: filter ?? 'pending',
        myRemindersOnly: !odoo.isAdmin,
      ),
      summaryBuilder: (items) {
        if (items.isEmpty) return null;
        final vencidos = items.where((r) => r.isOverdue).length;
        final hoy = items.where((r) => r.isToday).length;
        return TotalsBar(
          entries: [
            ('Total', '${items.length}'),
            ('Vencen hoy', '$hoy'),
            ('Vencidos', '$vencidos'),
          ],
        );
      },
      itemBuilder: (context, r) => ReminderTile(
        reminder: r,
        onTap: () => _edit(r),
        onToggleDone: () => _toggleDone(service, r),
      ),
    );
  }
}
