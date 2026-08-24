import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api/odoo_client.dart';
import '../../core/notifications/notification_service.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/app_badge.dart';
import '../../core/widgets/odoo_image.dart';
import '../../core/widgets/states.dart';
import '../auth/auth_service.dart';
import '../properties/property_detail_screen.dart';
import 'visit_form_screen.dart';
import 'visit_model.dart';
import 'visit_service.dart';

class VisitDetailScreen extends StatefulWidget {
  final int visitId;
  const VisitDetailScreen({super.key, required this.visitId});

  @override
  State<VisitDetailScreen> createState() => _VisitDetailScreenState();
}

class _VisitDetailScreenState extends State<VisitDetailScreen> {
  late final OdooClient _odoo;
  Visit? _visit;
  String? _clientPhone;
  bool _loading = true;
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _odoo = context.read<AuthService>().odoo;
    _load();
  }

  Future<void> _load() async {
    try {
      final rows = await _odoo.searchRead(
        model: 'calendar.event',
        domain: [
          ['id', '=', widget.visitId],
        ],
        fields: Visit.detailFields,
        limit: 1,
      );
      var visit = Visit.fromJson(rows.first);

      // Participantes: `partner_ids` llega como lista de ids, se resuelven
      // los nombres en una segunda consulta (solo en la ficha).
      final ids = rows.first['partner_ids'];
      if (ids is List && ids.isNotEmpty) {
        final partners = await _odoo.searchRead(
          model: 'res.partner',
          domain: [
            ['id', 'in', ids],
          ],
          fields: ['name'],
        );
        visit = visit.copyWithAttendees(
          partners
              .map((p) => (p['name'] ?? '').toString())
              .where((n) => n.isNotEmpty)
              .toList(),
        );
      }

      if (mounted) setState(() => _visit = visit);
      if (visit.clientId != null) _loadClientPhone(visit.clientId!);
    } catch (e) {
      if (mounted) setState(() => _error = 'No se pudo cargar la cita.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _loadClientPhone(int partnerId) async {
    try {
      final rows = await _odoo.searchRead(
        model: 'res.partner',
        domain: [
          ['id', '=', partnerId],
        ],
        fields: ['mobile', 'phone'],
        limit: 1,
      );
      if (rows.isEmpty) return;
      final phone = (rows.first['mobile'] ?? rows.first['phone'] ?? '')
          .toString();
      if (mounted && phone.isNotEmpty) setState(() => _clientPhone = phone);
    } catch (_) {
      // Sin teléfono, la ficha simplemente no ofrece llamar/WhatsApp.
    }
  }

  Future<void> _openEdit() async {
    final saved = await Navigator.of(context).push<bool>(
      MaterialPageRoute(builder: (_) => VisitFormScreen(existing: _visit)),
    );
    if (saved == true) _load();
  }

  /// Envía YA el recordatorio de WhatsApp, sin esperar al cron — llama al
  /// método del ERP, que usa la misma plantilla aprobada en Meta y avisa
  /// tanto al asesor como al cliente.
  Future<void> _sendReminder() async {
    final messenger = ScaffoldMessenger.of(context);
    setState(() => _busy = true);
    try {
      final result = await _odoo.callKw(
        model: 'calendar.event',
        method: 'action_send_reminder_now',
        args: [
          [widget.visitId],
        ],
      );
      final detail = result is Map ? (result['detail'] ?? '').toString() : '';
      messenger.showSnackBar(
        SnackBar(
          content: Text(detail.isEmpty ? 'Recordatorio procesado.' : detail),
        ),
      );
      await _load();
    } catch (e) {
      messenger.showSnackBar(
        const SnackBar(
          content: Text(
            'No se pudo enviar el recordatorio. '
            'Revisa la configuración de WhatsApp en el ERP.',
          ),
        ),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _sendFollowup() async {
    final messenger = ScaffoldMessenger.of(context);
    setState(() => _busy = true);
    try {
      await _odoo.callKw(
        model: 'calendar.event',
        method: 'action_send_whatsapp_followup',
        args: [
          [widget.visitId],
        ],
      );
      messenger.showSnackBar(
        const SnackBar(content: Text('Seguimiento enviado al cliente.')),
      );
      await _load();
    } catch (e) {
      messenger.showSnackBar(
        const SnackBar(content: Text('No se pudo enviar el seguimiento.')),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _closeVisit() async {
    final result =
        await showModalBottomSheet<
          ({String result, String rating, String notes})
        >(
          context: context,
          isScrollControlled: true,
          builder: (_) => _VisitResultSheet(initialNotes: _visit?.notes ?? ''),
        );
    if (result == null) return;

    setState(() => _busy = true);
    try {
      await VisitService(_odoo).update(widget.visitId, {
        'visit_state': 'done',
        'visit_result': result.result,
        if (result.rating.isNotEmpty) 'visit_rating': result.rating,
        if (result.notes.isNotEmpty) 'visit_notes': result.notes,
      });
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No se pudo cerrar la visita.')),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _setState(String state) async {
    setState(() => _busy = true);
    try {
      await VisitService(_odoo).update(widget.visitId, {'visit_state': state});
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('No se pudo actualizar el estado de la cita.'),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _delete() async {
    final p = AppColors.of(context);
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Eliminar cita'),
        content: const Text(
          '¿Seguro que quieres eliminar esta cita? '
          'También se quitará del calendario y de Google Calendar si está sincronizada.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            style: FilledButton.styleFrom(backgroundColor: p.danger),
            child: const Text('Eliminar'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    setState(() => _busy = true);
    try {
      await _odoo.unlink(model: 'calendar.event', id: widget.visitId);
      // La cita ya no existe: se retira también su aviso del teléfono.
      await NotificationService.instance.cancelVisit(widget.visitId);
      if (mounted) Navigator.of(context).pop(true);
    } catch (e) {
      if (mounted) {
        setState(() => _busy = false);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No se pudo eliminar la cita.')),
        );
      }
    }
  }

  Future<void> _call(String phone) async {
    final uri = Uri(scheme: 'tel', path: phone);
    if (await canLaunchUrl(uri)) await launchUrl(uri);
  }

  Future<void> _whatsapp(String phone) async {
    final digits = phone.replaceAll(RegExp(r'[^0-9]'), '');
    final uri = Uri.parse('https://wa.me/$digits');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  Future<void> _openLocationMaps(String location) async {
    if (location.isEmpty) return;
    final uri = Uri.parse(
      'https://www.google.com/maps/search/?api=1&query=${Uri.encodeComponent('$location Ecuador')}',
    );
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  Future<void> _openLocationWaze(String location) async {
    if (location.isEmpty) return;
    final uri = Uri.parse(
      'https://waze.com/ul?q=${Uri.encodeComponent('$location Ecuador')}&navigate=yes',
    );
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Detalle de la cita'),
        actions: [
          if (_visit != null) ...[
            IconButton(
              icon: const Icon(Icons.edit_outlined),
              onPressed: _busy ? null : _openEdit,
            ),
            IconButton(
              icon: const Icon(Icons.delete_outline),
              tooltip: 'Eliminar cita',
              onPressed: _busy ? null : _delete,
            ),
          ],
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
    final p = AppColors.of(context);
    final dayFmt = DateFormat("EEEE d 'de' MMMM, y", 'es_EC');
    final timeFmt = DateFormat.Hm('es_EC');
    final typeColor = AppointmentTypeStyle.color(v.appointmentType);

    return ListView(
      padding: EdgeInsets.zero,
      children: [
        // ── Cabecera con la hora en grande: es el dato que más se consulta
        Container(
          width: double.infinity,
          padding: const EdgeInsets.fromLTRB(
            AppSpace.xl,
            AppSpace.lg,
            AppSpace.xl,
            AppSpace.xl,
          ),
          decoration: BoxDecoration(
            color: typeColor.withValues(alpha: p.isDark ? 0.18 : 0.08),
            border: Border(bottom: BorderSide(color: p.line)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(AppSpace.sm),
                    decoration: BoxDecoration(
                      color: typeColor.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(AppRadius.sm),
                    ),
                    child: Icon(
                      AppointmentTypeStyle.icon(v.appointmentType),
                      size: 18,
                      color: typeColor,
                    ),
                  ),
                  const SizedBox(width: AppSpace.sm),
                  Text(
                    AppointmentTypeStyle.label(v.appointmentType).toUpperCase(),
                    style: AppType.label.copyWith(color: typeColor),
                  ),
                ],
              ),
              const SizedBox(height: AppSpace.md),
              Text(
                v.allDay ? 'Todo el día' : timeFmt.format(v.start),
                style: AppType.display.copyWith(fontSize: 34, color: p.ink),
              ),
              const SizedBox(height: 2),
              Text(
                dayFmt.format(v.start),
                style: AppType.body.copyWith(color: p.muted),
              ),
              if (v.duration != null && !v.allDay) ...[
                const SizedBox(height: 2),
                Text(
                  'Hasta ${timeFmt.format(v.stop!)} · ${_durationLabel(v.duration!)}',
                  style: AppType.caption.copyWith(color: p.mutedLight),
                ),
              ],
              const SizedBox(height: AppSpace.md),
              Wrap(
                spacing: AppSpace.sm,
                runSpacing: AppSpace.sm,
                children: [
                  AppBadge(
                    label: VisitStateStyle.label(v.visitState),
                    color: VisitStateStyle.color(v.visitState),
                  ),
                  if (v.visitResult.isNotEmpty)
                    AppBadge(
                      label: VisitResultStyle.label(v.visitResult),
                      color: VisitResultStyle.color(v.visitResult),
                    ),
                  if (v.visitRating.isNotEmpty)
                    AppBadge(
                      label: '${v.visitRating}/5',
                      icon: Icons.star,
                      color: (int.tryParse(v.visitRating) ?? 0) >= 4
                          ? p.success
                          : (int.tryParse(v.visitRating) ?? 0) <= 2
                          ? p.danger
                          : p.warning,
                    ),
                  if (v.whatsappSent)
                    AppBadge(
                      label: 'Recordatorio enviado',
                      icon: Icons.check,
                      color: p.success,
                    ),
                ],
              ),
            ],
          ),
        ),

        Padding(
          padding: const EdgeInsets.all(AppSpace.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (v.name.isNotEmpty) ...[
                Text(v.name, style: AppType.title.copyWith(color: p.ink)),
                const SizedBox(height: AppSpace.lg),
              ],

              // ── Propiedad, con foto y acceso a su ficha
              if (v.propertyId != null) ...[
                const _SectionLabel('Propiedad'),
                const SizedBox(height: AppSpace.sm),
                Card(
                  clipBehavior: Clip.antiAlias,
                  child: InkWell(
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) =>
                            PropertyDetailScreen(propertyId: v.propertyId!),
                      ),
                    ),
                    child: Row(
                      children: [
                        SizedBox(
                          width: 76,
                          height: 76,
                          child: OdooImage(
                            odoo: _odoo,
                            model: 'estate.property',
                            id: v.propertyId!,
                            field: 'image_main',
                            width: 180,
                            height: 180,
                          ),
                        ),
                        Expanded(
                          child: Padding(
                            padding: const EdgeInsets.symmetric(
                              horizontal: AppSpace.md,
                            ),
                            child: Text(
                              v.propertyName,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: AppType.body.copyWith(
                                fontWeight: FontWeight.w600,
                                color: p.ink,
                              ),
                            ),
                          ),
                        ),
                        Padding(
                          padding: const EdgeInsets.only(right: AppSpace.md),
                          child: Icon(Icons.chevron_right, color: p.mutedLight),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: AppSpace.lg),
              ],

              // ── Cliente, con contacto directo
              if (v.clientName.isNotEmpty) ...[
                const _SectionLabel('Cliente'),
                const SizedBox(height: AppSpace.sm),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(AppSpace.md),
                    child: Row(
                      children: [
                        InitialsAvatar(text: v.clientName, size: 42),
                        const SizedBox(width: AppSpace.md),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                v.clientName,
                                style: AppType.body.copyWith(
                                  fontWeight: FontWeight.w600,
                                  color: p.ink,
                                ),
                              ),
                              if (_clientPhone != null)
                                Text(
                                  _clientPhone!,
                                  style: AppType.caption.copyWith(
                                    color: p.muted,
                                  ),
                                ),
                            ],
                          ),
                        ),
                        if (_clientPhone != null) ...[
                          _RoundAction(
                            icon: Icons.call,
                            background: p.navy,
                            onTap: () => _call(_clientPhone!),
                          ),
                          const SizedBox(width: AppSpace.sm),
                          _RoundAction(
                            icon: Icons.chat,
                            background: const Color(0xFF25D366),
                            onTap: () => _whatsapp(_clientPhone!),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: AppSpace.lg),
              ],

              // ── Datos de la cita
              const _SectionLabel('Datos de la cita'),
              const SizedBox(height: AppSpace.sm),
              Card(
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpace.lg,
                    vertical: AppSpace.xs,
                  ),
                  child: Column(
                    children: [
                      if (v.userName.isNotEmpty)
                        _DetailRow(
                          icon: Icons.badge_outlined,
                          label: 'Asesor',
                          value: v.userName,
                        ),
                      if (v.location.isNotEmpty) ...[
                        _DetailRow(
                          icon: Icons.place_outlined,
                          label: 'Lugar',
                          value: v.location,
                        ),
                        Padding(
                          padding: const EdgeInsets.only(top: 4, bottom: 8),
                          child: Row(
                            children: [
                              Expanded(
                                child: OutlinedButton.icon(
                                  onPressed: () => _openLocationMaps(v.location),
                                  style: OutlinedButton.styleFrom(
                                    padding: const EdgeInsets.symmetric(vertical: 8),
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(10),
                                    ),
                                  ),
                                  icon: const Icon(Icons.location_on_outlined, size: 16, color: Color(0xFFEA4335)),
                                  label: const Text('Google Maps', style: TextStyle(fontSize: 12)),
                                ),
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: OutlinedButton.icon(
                                  onPressed: () => _openLocationWaze(v.location),
                                  style: OutlinedButton.styleFrom(
                                    padding: const EdgeInsets.symmetric(vertical: 8),
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(10),
                                    ),
                                  ),
                                  icon: const Icon(Icons.navigation_rounded, size: 16, color: Color(0xFF33CCFF)),
                                  label: const Text('Waze GPS', style: TextStyle(fontSize: 12)),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                      _DetailRow(
                        icon: Icons.notifications_active_outlined,
                        label: 'Recordatorio',
                        value: v.reminderValue > 0
                            ? '${v.reminderValue} ${ReminderUnitStyle.label(v.reminderUnit)} antes'
                            : 'Según la configuración del asesor',
                      ),
                      _DetailRow(
                        icon: Icons.chat_outlined,
                        label: 'WhatsApp',
                        value: v.whatsappSent
                            ? 'Recordatorio ya enviado'
                            : 'Sin enviar todavía',
                        valueColor: v.whatsappSent ? p.success : p.muted,
                      ),
                      if (v.attendeeNames.isNotEmpty)
                        _DetailRow(
                          icon: Icons.groups_outlined,
                          label: 'Participantes',
                          value: v.attendeeNames.join(', '),
                        ),
                    ],
                  ),
                ),
              ),

              // ── Notas y descripción
              if (v.notes.isNotEmpty) ...[
                const SizedBox(height: AppSpace.lg),
                const _SectionLabel('Notas de la visita'),
                const SizedBox(height: AppSpace.sm),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(AppSpace.lg),
                    child: SelectableText(
                      v.notes,
                      style: AppType.body.copyWith(color: p.ink),
                    ),
                  ),
                ),
              ],
              if (v.description.isNotEmpty) ...[
                const SizedBox(height: AppSpace.lg),
                const _SectionLabel('Descripción'),
                const SizedBox(height: AppSpace.sm),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(AppSpace.lg),
                    child: SelectableText(
                      v.description,
                      style: AppType.body.copyWith(color: p.ink),
                    ),
                  ),
                ),
              ],

              // ── Acciones de WhatsApp
              const SizedBox(height: AppSpace.lg),
              const _SectionLabel('WhatsApp'),
              const SizedBox(height: AppSpace.sm),
              if (v.visitState == 'scheduled')
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    onPressed: _busy ? null : _sendReminder,
                    icon: const Icon(
                      Icons.notifications_active_outlined,
                      size: 18,
                    ),
                    label: Text(
                      v.whatsappSent
                          ? 'Reenviar recordatorio ahora'
                          : 'Enviar recordatorio ahora',
                    ),
                  ),
                ),
              if (v.visitState == 'done')
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    onPressed: _busy ? null : _sendFollowup,
                    icon: const Icon(Icons.reply_outlined, size: 18),
                    label: const Text('Enviar seguimiento post-visita'),
                  ),
                ),

              // ── Cierre de la visita
              if (v.visitState == 'scheduled') ...[
                const SizedBox(height: AppSpace.lg),
                Row(
                  children: [
                    Expanded(
                      child: FilledButton.icon(
                        onPressed: _busy ? null : _closeVisit,
                        style: FilledButton.styleFrom(
                          backgroundColor: p.success,
                        ),
                        icon: const Icon(Icons.check_circle_outline, size: 18),
                        label: const Text('Realizada'),
                      ),
                    ),
                    const SizedBox(width: AppSpace.sm),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _busy ? null : () => _setState('cancelled'),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: p.danger,
                          side: BorderSide(color: p.danger),
                        ),
                        icon: const Icon(Icons.cancel_outlined, size: 18),
                        label: const Text('Cancelar'),
                      ),
                    ),
                  ],
                ),
              ],
              const SizedBox(height: AppSpace.xxl),
            ],
          ),
        ),
      ],
    );
  }

  String _durationLabel(Duration d) {
    if (d.inMinutes < 60) return '${d.inMinutes} min';
    final h = d.inHours;
    final m = d.inMinutes % 60;
    return m == 0 ? '$h h' : '$h h $m min';
  }
}

class _SectionLabel extends StatelessWidget {
  final String text;
  const _SectionLabel(this.text);

  @override
  Widget build(BuildContext context) {
    final p = AppColors.of(context);
    return Text(
      text.toUpperCase(),
      style: AppType.label.copyWith(color: p.mutedLight),
    );
  }
}

class _DetailRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color? valueColor;
  const _DetailRow({
    required this.icon,
    required this.label,
    required this.value,
    this.valueColor,
  });

  @override
  Widget build(BuildContext context) {
    final p = AppColors.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpace.md),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 17, color: p.navy),
          const SizedBox(width: AppSpace.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: AppType.caption.copyWith(color: p.mutedLight),
                ),
                const SizedBox(height: 1),
                Text(
                  value,
                  style: AppType.bodySmall.copyWith(
                    fontWeight: FontWeight.w600,
                    color: valueColor ?? p.ink,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _RoundAction extends StatelessWidget {
  final IconData icon;
  final Color background;
  final VoidCallback onTap;
  const _RoundAction({
    required this.icon,
    required this.background,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(AppRadius.pill),
      onTap: onTap,
      child: Container(
        width: 38,
        height: 38,
        decoration: BoxDecoration(color: background, shape: BoxShape.circle),
        child: Icon(icon, color: Colors.white, size: 18),
      ),
    );
  }
}

/// Hoja para cerrar una visita: resultado, calificación del cliente y
/// observaciones. Es el paso que alimenta el puntaje del lead en el ERP.
class _VisitResultSheet extends StatefulWidget {
  final String initialNotes;
  const _VisitResultSheet({required this.initialNotes});

  @override
  State<_VisitResultSheet> createState() => _VisitResultSheetState();
}

class _VisitResultSheetState extends State<_VisitResultSheet> {
  String _result = 'interested';
  String _rating = '';
  late final TextEditingController _notesCtrl = TextEditingController(
    text: widget.initialNotes,
  );

  @override
  void dispose() {
    _notesCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final p = AppColors.of(context);
    return Padding(
      padding: EdgeInsets.fromLTRB(
        AppSpace.xl,
        AppSpace.lg,
        AppSpace.xl,
        MediaQuery.of(context).viewInsets.bottom + AppSpace.xl,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '¿Cómo salió la visita?',
            style: AppType.title.copyWith(color: p.ink),
          ),
          const SizedBox(height: AppSpace.lg),
          Text(
            'Resultado',
            style: AppType.caption.copyWith(color: p.mutedLight),
          ),
          const SizedBox(height: AppSpace.sm),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: VisitResultStyle.options.map((o) {
              final selected = _result == o.$1;
              return ChoiceChip(
                label: Text(o.$2),
                selected: selected,
                onSelected: (_) => setState(() => _result = o.$1),
                selectedColor: VisitResultStyle.color(o.$1),
                backgroundColor: p.neutralBg,
                labelStyle: TextStyle(
                  color: selected ? Colors.white : p.ink,
                  fontWeight: FontWeight.w600,
                  fontSize: 12.5,
                ),
                side: BorderSide.none,
                showCheckmark: false,
              );
            }).toList(),
          ),
          const SizedBox(height: AppSpace.lg),
          Text(
            'Calificación del cliente',
            style: AppType.caption.copyWith(color: p.mutedLight),
          ),
          const SizedBox(height: AppSpace.sm),
          Row(
            children: List.generate(5, (i) {
              final value = '${i + 1}';
              final active = _rating.isNotEmpty && int.parse(_rating) >= i + 1;
              return IconButton(
                onPressed: () => setState(() => _rating = value),
                icon: Icon(
                  active ? Icons.star : Icons.star_border,
                  color: active ? p.warning : p.mutedLight,
                  size: 30,
                ),
                padding: const EdgeInsets.symmetric(horizontal: 2),
                constraints: const BoxConstraints(),
              );
            }),
          ),
          const SizedBox(height: AppSpace.lg),
          TextField(
            controller: _notesCtrl,
            minLines: 3,
            maxLines: 5,
            decoration: const InputDecoration(
              labelText: 'Observaciones de la visita',
              alignLabelWithHint: true,
            ),
          ),
          const SizedBox(height: AppSpace.xl),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: () => Navigator.of(context).pop((
                result: _result,
                rating: _rating,
                notes: _notesCtrl.text.trim(),
              )),
              child: const Text('Cerrar visita'),
            ),
          ),
        ],
      ),
    );
  }
}
