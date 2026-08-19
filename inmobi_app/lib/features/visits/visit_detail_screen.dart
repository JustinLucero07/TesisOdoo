import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/app_badge.dart';
import '../../core/widgets/states.dart';
import '../auth/auth_service.dart';
import 'visit_form_screen.dart';
import 'visit_model.dart';

class VisitDetailScreen extends StatefulWidget {
  final int visitId;
  const VisitDetailScreen({super.key, required this.visitId});

  @override
  State<VisitDetailScreen> createState() => _VisitDetailScreenState();
}

class _VisitDetailScreenState extends State<VisitDetailScreen> {
  Visit? _visit;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final odoo = context.read<AuthService>().odoo;
      final rows = await odoo.searchRead(
        model: 'calendar.event',
        domain: [
          ['id', '=', widget.visitId],
        ],
        fields: Visit.listFields,
        limit: 1,
      );
      setState(() => _visit = Visit.fromJson(rows.first));
    } catch (e) {
      setState(() => _error = 'No se pudo cargar la visita.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _openEdit() async {
    final saved = await Navigator.of(context).push<bool>(
      MaterialPageRoute(builder: (_) => VisitFormScreen(existing: _visit)),
    );
    if (saved == true) _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Cita'),
        actions: [
          if (_visit != null)
            IconButton(
              icon: const Icon(Icons.edit_outlined),
              onPressed: _openEdit,
            ),
        ],
      ),
      body: _loading
          ? const LoadingView()
          : _error != null
          ? MessageView(
              icon: Icons.error_outline,
              message: _error!,
              onRetry: _load,
            )
          : _buildBody(),
    );
  }

  Widget _buildBody() {
    final v = _visit!;
    final dateFmt = DateFormat("EEEE d 'de' MMMM, y · HH:mm", 'es_EC');
    return ListView(
      padding: const EdgeInsets.all(18),
      children: [
        Row(
          children: [
            Icon(
              AppointmentTypeStyle.icon(v.appointmentType),
              color: AppColors.navy,
            ),
            const SizedBox(width: 8),
            Text(
              AppointmentTypeStyle.label(v.appointmentType),
              style: const TextStyle(
                fontSize: 13,
                color: AppColors.muted,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          v.propertyName.isNotEmpty ? v.propertyName : v.name,
          style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        AppBadge(
          label: VisitStateStyle.label(v.visitState),
          color: VisitStateStyle.color(v.visitState),
        ),
        const SizedBox(height: 20),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.schedule, size: 17, color: AppColors.navy),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        dateFmt.format(v.start),
                        style: const TextStyle(fontSize: 13.5),
                      ),
                    ),
                  ],
                ),
                if (v.clientName.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      const Icon(
                        Icons.person_outline,
                        size: 17,
                        color: AppColors.navy,
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          v.clientName,
                          style: const TextStyle(fontSize: 13.5),
                        ),
                      ),
                    ],
                  ),
                ],
              ],
            ),
          ),
        ),
        if (v.notes.isNotEmpty) ...[
          const SizedBox(height: 14),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Notas',
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 13,
                      color: AppColors.muted,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(v.notes, style: const TextStyle(fontSize: 13.5)),
                ],
              ),
            ),
          ),
        ],
      ],
    );
  }
}
