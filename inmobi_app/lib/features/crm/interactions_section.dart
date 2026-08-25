import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/api/odoo_client.dart';
import '../../core/api/odoo_json.dart';
import '../../core/theme/app_theme.dart';

class Interaction {
  final int id;
  final DateTime date;
  final String type;
  final String summary;
  final String userName;

  Interaction({
    required this.id,
    required this.date,
    required this.type,
    required this.summary,
    required this.userName,
  });

  factory Interaction.fromJson(Map<String, dynamic> json) {
    return Interaction(
      id: json['id'] as int,
      date: DateTime.parse(
        '${asOdooString(json['date']).replaceFirst(' ', 'T')}Z',
      ).toLocal(),
      type: asOdooString(json['interaction_type'], 'other'),
      summary: asOdooString(json['summary']),
      userName: many2oneName(json['user_id']),
    );
  }

  static IconData iconOf(String type) => switch (type) {
    'note' => Icons.sticky_note_2_outlined,
    'call' => Icons.call_outlined,
    'email' => Icons.email_outlined,
    'visit' => Icons.home_outlined,
    'meeting' => Icons.groups_outlined,
    'whatsapp' => Icons.chat_outlined,
    _ => Icons.circle_outlined,
  };

  static String labelOf(String type) => switch (type) {
    'note' => 'Nota Chatter',
    'call' => 'Llamada',
    'email' => 'Correo',
    'visit' => 'Visita',
    'meeting' => 'Reunión',
    'whatsapp' => 'WhatsApp',
    _ => 'Otro',
  };

  static Color colorOf(String type) => switch (type) {
    'note' => const Color(0xFFD81F26),
    'call' => AppColors.navy,
    'email' => AppColors.info,
    'visit' => AppColors.success,
    'meeting' => AppColors.navyLight,
    'whatsapp' => const Color(0xFF25D366),
    _ => AppColors.mutedLight,
  };
}

/// Bitácora de interacciones con el cliente (`estate.client.interaction`) —
/// la misma que se registra en el ERP. Se muestra como línea de tiempo y
/// permite registrar una nueva sin salir del lead.
class InteractionsSection extends StatefulWidget {
  final OdooClient odoo;
  final int leadId;
  final int? partnerId;
  final int? propertyId;

  const InteractionsSection({
    super.key,
    required this.odoo,
    required this.leadId,
    this.partnerId,
    this.propertyId,
  });

  @override
  State<InteractionsSection> createState() => _InteractionsSectionState();
}

class _InteractionsSectionState extends State<InteractionsSection> {
  List<Interaction> _items = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final rows = await widget.odoo.searchRead(
        model: 'estate.client.interaction',
        domain: [
          ['lead_id', '=', widget.leadId],
        ],
        fields: ['date', 'interaction_type', 'summary', 'user_id'],
        order: 'date desc',
        limit: 50,
      );
      if (mounted)
        setState(() => _items = rows.map(Interaction.fromJson).toList());
    } catch (_) {
      // Silencioso: la sección queda vacía si falla.
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _addInteraction() async {
    final result = await showModalBottomSheet<({String type, String summary})>(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => const _NewInteractionSheet(),
    );
    if (result == null) return;

    try {
      try {
        await widget.odoo.create(
          model: 'estate.client.interaction',
          values: {
            'lead_id': widget.leadId,
            if (widget.partnerId != null) 'partner_id': widget.partnerId,
            if (widget.propertyId != null) 'property_id': widget.propertyId,
            'interaction_type': result.type,
            'summary': result.summary,
          },
        );
      } catch (_) {}

      // También postear en el Chatter oficial de Odoo (mail.message)
      try {
        final prefix = result.type == 'note'
            ? '<b>Nota de seguimiento:</b><br/>'
            : '<b>[${Interaction.labelOf(result.type)}]</b><br/>';
        await widget.odoo.callKw(
          model: 'crm.lead',
          method: 'message_post',
          args: [
            [widget.leadId],
          ],
          kwargs: {
            'body': '$prefix${result.summary}',
            'message_type': 'comment',
            'subtype_xmlid': 'mail.mt_note',
          },
        );
      } catch (_) {}

      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'No se pudo registrar la nota/interacción.',
            ),
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final dateFmt = DateFormat('d MMM y · HH:mm', 'es_EC');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(
              'Interacciones${_items.isNotEmpty ? ' (${_items.length})' : ''}',
              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
            ),
            const Spacer(),
            TextButton.icon(
              onPressed: _addInteraction,
              icon: const Icon(Icons.add_comment_outlined, size: 17),
              label: const Text('Registrar'),
            ),
          ],
        ),
        if (_loading)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 12),
            child: LinearProgressIndicator(),
          )
        else if (_items.isEmpty)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 8),
            child: Text(
              'Sin interacciones registradas.',
              style: TextStyle(color: AppColors.mutedLight, fontSize: 13),
            ),
          )
        else
          Column(
            children: [
              for (int i = 0; i < _items.length; i++)
                _TimelineTile(
                  interaction: _items[i],
                  isLast: i == _items.length - 1,
                  dateFmt: dateFmt,
                ),
            ],
          ),
      ],
    );
  }
}

/// Fila de la línea de tiempo: punto de color + línea vertical de conexión.
class _TimelineTile extends StatelessWidget {
  final Interaction interaction;
  final bool isLast;
  final DateFormat dateFmt;

  const _TimelineTile({
    required this.interaction,
    required this.isLast,
    required this.dateFmt,
  });

  @override
  Widget build(BuildContext context) {
    final color = Interaction.colorOf(interaction.type);
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Column(
            children: [
              Container(
                width: 30,
                height: 30,
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.12),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  Interaction.iconOf(interaction.type),
                  size: 15,
                  color: color,
                ),
              ),
              if (!isLast)
                Expanded(child: Container(width: 2, color: AppColors.line)),
            ],
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Padding(
              padding: EdgeInsets.only(bottom: isLast ? 0 : 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        Interaction.labelOf(interaction.type),
                        style: TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 12.5,
                          color: color,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          dateFmt.format(interaction.date),
                          style: const TextStyle(
                            fontSize: 11,
                            color: AppColors.mutedLight,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 3),
                  Text(
                    interaction.summary,
                    style: const TextStyle(fontSize: 13, height: 1.35),
                  ),
                  if (interaction.userName.isNotEmpty) ...[
                    const SizedBox(height: 3),
                    Text(
                      interaction.userName,
                      style: const TextStyle(
                        fontSize: 11,
                        color: AppColors.mutedLight,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _NewInteractionSheet extends StatefulWidget {
  const _NewInteractionSheet();

  @override
  State<_NewInteractionSheet> createState() => _NewInteractionSheetState();
}

class _NewInteractionSheetState extends State<_NewInteractionSheet> {
  String _type = 'call';
  final _summaryCtrl = TextEditingController();

  static const _types = [
    ('note', 'Nota Chatter'),
    ('call', 'Llamada'),
    ('whatsapp', 'WhatsApp'),
    ('meeting', 'Reunión'),
    ('visit', 'Visita'),
    ('email', 'Correo'),
    ('other', 'Otro'),
  ];

  @override
  void dispose() {
    _summaryCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(
        20,
        12,
        20,
        MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              width: 38,
              height: 4,
              decoration: BoxDecoration(
                color: AppColors.line,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 18),
          const Text(
            'Registrar interacción',
            style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: _types.map((t) {
              final selected = _type == t.$1;
              return ChoiceChip(
                avatar: Icon(
                  Interaction.iconOf(t.$1),
                  size: 15,
                  color: selected ? Colors.white : Interaction.colorOf(t.$1),
                ),
                label: Text(t.$2),
                selected: selected,
                onSelected: (_) => setState(() => _type = t.$1),
                selectedColor: AppColors.navy,
                backgroundColor: AppColors.neutralBg,
                labelStyle: TextStyle(
                  color: selected ? Colors.white : AppColors.ink,
                  fontWeight: FontWeight.w600,
                  fontSize: 12.5,
                ),
                side: BorderSide.none,
                showCheckmark: false,
              );
            }).toList(),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _summaryCtrl,
            minLines: 3,
            maxLines: 5,
            autofocus: true,
            decoration: const InputDecoration(
              labelText: 'Resumen de la interacción',
              alignLabelWithHint: true,
            ),
          ),
          const SizedBox(height: 18),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: () {
                final summary = _summaryCtrl.text.trim();
                if (summary.isEmpty) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Escribe un resumen de la interacción.'),
                    ),
                  );
                  return;
                }
                Navigator.of(context).pop((type: _type, summary: summary));
              },
              child: const Text('Guardar'),
            ),
          ),
        ],
      ),
    );
  }
}
