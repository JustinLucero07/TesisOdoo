import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/api/odoo_client.dart';
import '../../core/api/odoo_json.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/html_text.dart';

/// Un mensaje del chatter de Odoo (el panel de la derecha en la ficha).
class ChatterMessage {
  final int id;
  final String body;
  final String authorName;
  final DateTime? date;
  final bool isNote;

  const ChatterMessage({
    required this.id,
    required this.body,
    required this.authorName,
    this.date,
    this.isNote = true,
  });
}

/// Muestra y permite escribir en el chatter de cualquier ficha de Odoo.
///
/// Es lo que en Odoo aparece a la derecha con "Enviar mensaje" y "Registrar
/// una nota": hasta ahora la app solo escribía ahí, sin poder leerlo.
class ChatterSection extends StatefulWidget {
  final OdooClient odoo;
  final String model;
  final int resId;

  const ChatterSection({
    super.key,
    required this.odoo,
    required this.model,
    required this.resId,
  });

  @override
  State<ChatterSection> createState() => _ChatterSectionState();
}

class _ChatterSectionState extends State<ChatterSection> {
  List<ChatterMessage> _items = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(covariant ChatterSection old) {
    super.didUpdateWidget(old);
    if (old.resId != widget.resId || old.model != widget.model) _load();
  }

  /// Id del subtipo "nota interna", para distinguirla de un mensaje público.
  Future<int?> _noteSubtypeId() async {
    try {
      final res = await widget.odoo.callKw(
        model: 'ir.model.data',
        method: 'check_object_reference',
        args: ['mail', 'mt_note'],
      );
      if (res is List && res.length > 1 && res[1] is int) return res[1] as int;
    } catch (_) {
      // Sin esto solo se pierde la etiqueta Nota/Mensaje, no la lectura.
    }
    return null;
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final noteId = await _noteSubtypeId();
      final rows = await widget.odoo.searchRead(
        model: 'mail.message',
        domain: [
          ['model', '=', widget.model],
          ['res_id', '=', widget.resId],
        ],
        fields: ['date', 'body', 'author_id', 'subtype_id', 'message_type'],
        order: 'date desc',
        limit: 40,
      );

      final items = <ChatterMessage>[];
      for (final r in rows) {
        final texto = HtmlText.toPlain(asOdooString(r['body'])).trim();
        // Odoo guarda también mensajes sin cuerpo que solo registran cambios
        // de campo: en la app no aportan nada.
        if (texto.isEmpty) continue;
        final subtipo = r['subtype_id'] is List
            ? r['subtype_id'][0] as int
            : null;
        items.add(
          ChatterMessage(
            id: r['id'] as int,
            body: texto,
            authorName: many2oneName(r['author_id']),
            date: r['date'] is String
                ? DateTime.tryParse(
                    '${(r['date'] as String).replaceFirst(' ', 'T')}Z',
                  )?.toLocal()
                : null,
            isNote: noteId == null || subtipo == null || subtipo == noteId,
          ),
        );
      }
      if (mounted) setState(() => _items = items);
    } catch (_) {
      if (mounted) setState(() => _items = []);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _escribir() async {
    final result = await showModalBottomSheet<_NuevoMensaje>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => const _ChatterComposeSheet(),
    );
    if (result == null || !mounted) return;

    final messenger = ScaffoldMessenger.of(context);
    try {
      // El chatter guarda HTML: se escapa el texto y se respetan los saltos.
      final cuerpo = result.texto
          .replaceAll('&', '&amp;')
          .replaceAll('<', '&lt;')
          .replaceAll('>', '&gt;')
          .replaceAll('\n', '<br/>');
      await widget.odoo.callKw(
        model: widget.model,
        method: 'message_post',
        args: [
          [widget.resId],
        ],
        kwargs: {
          'body': '<p>$cuerpo</p>',
          'message_type': 'comment',
          'subtype_xmlid': result.esNota ? 'mail.mt_note' : 'mail.mt_comment',
        },
      );
      await _load();
      messenger.showSnackBar(
        SnackBar(
          content: Text(
            result.esNota
                ? 'Nota interna registrada.'
                : 'Mensaje enviado a los seguidores.',
          ),
        ),
      );
    } catch (_) {
      messenger.showSnackBar(
        const SnackBar(
          content: Text('No se pudo publicar en la conversación.'),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colors = AppColors.of(context);
    final dateFmt = DateFormat('d MMM y · HH:mm', 'es_EC');

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(
              'Conversación${_items.isNotEmpty ? ' (${_items.length})' : ''}',
              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
            ),
            const Spacer(),
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
              onPressed: _escribir,
              icon: const Icon(Icons.edit_note_rounded, size: 17),
              label: const Text('Escribir', style: TextStyle(fontSize: 12.5)),
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
                Icon(Icons.forum_outlined, size: 34, color: colors.mutedLight),
                const SizedBox(height: 6),
                Text(
                  'Sin mensajes en la conversación.',
                  style: TextStyle(
                    fontSize: 13,
                    color: colors.muted,
                    fontWeight: FontWeight.w500,
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
            itemBuilder: (context, i) {
              final m = _items[i];
              return Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF1E1A3E) : Colors.white,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: isDark ? Colors.white12 : colors.line,
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          m.isNote
                              ? Icons.sticky_note_2_outlined
                              : Icons.send_rounded,
                          size: 14,
                          color: m.isNote ? colors.warning : colors.info,
                        ),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            m.authorName.isNotEmpty ? m.authorName : 'Sistema',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontWeight: FontWeight.w700,
                              fontSize: 12.5,
                            ),
                          ),
                        ),
                        if (m.date != null)
                          Text(
                            dateFmt.format(m.date!),
                            style: TextStyle(
                              fontSize: 11,
                              color: colors.mutedLight,
                            ),
                          ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    SelectableText(
                      m.body,
                      style: TextStyle(
                        fontSize: 13,
                        height: 1.45,
                        color: colors.ink,
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
      ],
    );
  }
}

class _NuevoMensaje {
  final String texto;
  final bool esNota;
  const _NuevoMensaje(this.texto, this.esNota);
}

class _ChatterComposeSheet extends StatefulWidget {
  const _ChatterComposeSheet();

  @override
  State<_ChatterComposeSheet> createState() => _ChatterComposeSheetState();
}

class _ChatterComposeSheetState extends State<_ChatterComposeSheet> {
  final _ctrl = TextEditingController();
  bool _esNota = true;

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.of(context);
    return Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: Container(
        decoration: BoxDecoration(
          color: Theme.of(context).scaffoldBackgroundColor,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
        ),
        padding: const EdgeInsets.fromLTRB(18, 16, 18, 22),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Escribir en la conversación',
              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
            ),
            const SizedBox(height: 14),
            SegmentedButton<bool>(
              segments: const [
                ButtonSegment(
                  value: true,
                  icon: Icon(Icons.sticky_note_2_outlined, size: 16),
                  label: Text('Nota interna'),
                ),
                ButtonSegment(
                  value: false,
                  icon: Icon(Icons.send_rounded, size: 16),
                  label: Text('Mensaje'),
                ),
              ],
              selected: {_esNota},
              onSelectionChanged: (s) => setState(() => _esNota = s.first),
            ),
            const SizedBox(height: 6),
            Text(
              _esNota
                  ? 'Solo la ve el equipo dentro de Odoo.'
                  : 'Se envía por correo a los seguidores de la ficha.',
              style: TextStyle(fontSize: 11.5, color: colors.muted),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: _ctrl,
              maxLines: 5,
              autofocus: true,
              textCapitalization: TextCapitalization.sentences,
              decoration: const InputDecoration(
                hintText: 'Escribe aquí...',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text('Cancelar'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: FilledButton.icon(
                    onPressed: () {
                      final texto = _ctrl.text.trim();
                      if (texto.isEmpty) return;
                      Navigator.pop(context, _NuevoMensaje(texto, _esNota));
                    },
                    icon: const Icon(Icons.check_rounded, size: 18),
                    label: const Text('Publicar'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
