import 'dart:convert';
import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:open_file/open_file.dart';
import 'package:path_provider/path_provider.dart';

import '../../core/api/odoo_client.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/app_badge.dart';
import '../../core/widgets/many2one_field.dart';
import 'document_model.dart';
import 'document_service.dart';

/// Sección "Documentos" reutilizable — misma lista + subir + abrir para
/// Propiedad, Lead y Contrato, todos contra el modelo `estate.document` que
/// ya usa el ERP (con su tipo, estado y previsualización de PDF).
class DocumentsSection extends StatefulWidget {
  final OdooClient odoo;
  final DocumentOwner owner;
  const DocumentsSection({super.key, required this.odoo, required this.owner});

  @override
  State<DocumentsSection> createState() => _DocumentsSectionState();
}

class _DocumentsSectionState extends State<DocumentsSection> {
  late final DocumentService _service;
  List<EstateDocument> _docs = [];
  bool _loading = true;
  int? _openingId;

  @override
  void initState() {
    super.initState();
    _service = DocumentService(widget.odoo);
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final docs = await _service.list(widget.owner);
      if (mounted) setState(() => _docs = docs);
    } catch (_) {
      // Silencioso: la sección simplemente queda vacía si falla.
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  /// Verificar / rechazar / archivar — se llaman los MISMOS métodos del
  /// modelo (`action_verify`, `action_reject`…), así que quedan registrados
  /// en el chatter con el usuario y la fecha, igual que desde el ERP.
  Future<void> _runAction(
    EstateDocument doc,
    String method,
    String okMsg,
  ) async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      await widget.odoo.callKw(
        model: 'estate.document',
        method: method,
        args: [
          [doc.id],
        ],
      );
      messenger.showSnackBar(SnackBar(content: Text(okMsg)));
      _load();
    } catch (e) {
      messenger.showSnackBar(
        const SnackBar(
          content: Text('Odoo rechazó la acción sobre el documento.'),
        ),
      );
    }
  }

  void _showActions(EstateDocument doc) {
    showModalBottomSheet(
      context: context,
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(height: AppSpace.sm),
            ListTile(
              leading: const Icon(Icons.open_in_new),
              title: const Text('Abrir documento'),
              onTap: () {
                Navigator.pop(ctx);
                _open(doc);
              },
            ),
            if (doc.state != 'verified')
              ListTile(
                leading: const Icon(
                  Icons.verified_outlined,
                  color: AppColors.success,
                ),
                title: const Text('Marcar como verificado'),
                onTap: () {
                  Navigator.pop(ctx);
                  _runAction(doc, 'action_verify', 'Documento verificado.');
                },
              ),
            if (doc.state != 'rejected')
              ListTile(
                leading: const Icon(
                  Icons.cancel_outlined,
                  color: AppColors.danger,
                ),
                title: const Text('Rechazar documento'),
                onTap: () {
                  Navigator.pop(ctx);
                  _runAction(doc, 'action_reject', 'Documento rechazado.');
                },
              ),
            const SizedBox(height: AppSpace.sm),
          ],
        ),
      ),
    );
  }

  Future<void> _open(EstateDocument doc) async {
    setState(() => _openingId = doc.id);
    try {
      final bytes = await widget.odoo.downloadBytes(
        model: 'estate.document',
        id: doc.id,
        field: 'file',
      );
      final dir = await getTemporaryDirectory();
      final safeName = doc.filename.isNotEmpty
          ? doc.filename
          : '${doc.name}.bin';
      final file = File('${dir.path}/$safeName');
      await file.writeAsBytes(bytes);
      await OpenFile.open(file.path);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No se pudo abrir el documento.')),
        );
      }
    } finally {
      if (mounted) setState(() => _openingId = null);
    }
  }

  Future<void> _uploadFlow() async {
    final picked = await FilePicker.platform.pickFiles(withData: true);
    if (picked == null || picked.files.isEmpty) return;
    final file = picked.files.single;
    if (file.bytes == null) return;
    if (!mounted) return;

    final result = await showModalBottomSheet<_UploadResult>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _UploadSheet(odoo: widget.odoo, defaultName: file.name),
    );
    if (result == null) return;

    try {
      final base64File = base64Encode(file.bytes!);
      await _service.upload(
        owner: widget.owner,
        name: result.name,
        filename: file.name,
        base64File: base64File,
        typeId: result.typeId,
      );
      _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No se pudo subir el documento.')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final dateFmt = DateFormat('d MMM yyyy', 'es_EC');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Text(
              'Documentos',
              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
            ),
            const Spacer(),
            TextButton.icon(
              onPressed: _uploadFlow,
              icon: const Icon(Icons.upload_file_outlined, size: 17),
              label: const Text('Subir'),
            ),
          ],
        ),
        const SizedBox(height: 4),
        if (_loading)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 12),
            child: LinearProgressIndicator(),
          )
        else if (_docs.isEmpty)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 10),
            child: Text(
              'Sin documentos cargados.',
              style: TextStyle(color: AppColors.mutedLight, fontSize: 13),
            ),
          )
        else
          Card(
            child: Column(
              children: [
                for (int i = 0; i < _docs.length; i++) ...[
                  if (i > 0) const Divider(height: 1),
                  _DocumentTile(
                    doc: _docs[i],
                    opening: _openingId == _docs[i].id,
                    onTap: () => _open(_docs[i]),
                    onLongPress: () => _showActions(_docs[i]),
                    dateFmt: dateFmt,
                  ),
                ],
              ],
            ),
          ),
      ],
    );
  }
}

class _DocumentTile extends StatelessWidget {
  final EstateDocument doc;
  final bool opening;
  final VoidCallback onTap;
  final VoidCallback onLongPress;
  final DateFormat dateFmt;
  const _DocumentTile({
    required this.doc,
    required this.opening,
    required this.onTap,
    required this.onLongPress,
    required this.dateFmt,
  });

  @override
  Widget build(BuildContext context) {
    return ListTile(
      onTap: opening ? null : onTap,
      onLongPress: opening ? null : onLongPress,
      leading: Icon(doc.icon, color: AppColors.navy),
      title: Text(doc.name, maxLines: 1, overflow: TextOverflow.ellipsis),
      subtitle: Text(
        doc.typeName.isNotEmpty
            ? '${doc.typeName}${doc.date != null ? ' · ${dateFmt.format(doc.date!)}' : ''}'
            : (doc.date != null ? dateFmt.format(doc.date!) : ''),
        style: const TextStyle(fontSize: 12),
      ),
      trailing: opening
          ? const SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : AppBadge(
              label: DocumentStateStyle.label(doc.state),
              color: DocumentStateStyle.color(doc.state),
            ),
    );
  }
}

class _UploadResult {
  final String name;
  final int typeId;
  _UploadResult(this.name, this.typeId);
}

class _UploadSheet extends StatefulWidget {
  final OdooClient odoo;
  final String defaultName;
  const _UploadSheet({required this.odoo, required this.defaultName});

  @override
  State<_UploadSheet> createState() => _UploadSheetState();
}

class _UploadSheetState extends State<_UploadSheet> {
  late final TextEditingController _nameCtrl;
  Many2oneValue? _type;

  @override
  void initState() {
    super.initState();
    _nameCtrl = TextEditingController(text: widget.defaultName);
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(
        20,
        20,
        20,
        MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Subir documento',
            style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _nameCtrl,
            decoration: const InputDecoration(
              labelText: 'Nombre del documento',
            ),
          ),
          const SizedBox(height: 14),
          Many2oneField(
            label: 'Tipo de documento',
            required: true,
            odoo: widget.odoo,
            model: 'estate.document.type',
            value: _type,
            onChanged: (v) => setState(() => _type = v),
          ),
          const SizedBox(height: 20),
          ElevatedButton(
            onPressed: () {
              final name = _nameCtrl.text.trim();
              if (name.isEmpty || _type == null) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Completa el nombre y el tipo de documento.'),
                  ),
                );
                return;
              }
              Navigator.of(context).pop(_UploadResult(name, _type!.id));
            },
            child: const Text('Subir'),
          ),
        ],
      ),
    );
  }
}
