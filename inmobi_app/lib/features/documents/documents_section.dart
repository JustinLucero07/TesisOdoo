import 'dart:io';

import 'package:flutter/material.dart';
import 'package:gal/gal.dart';
import 'package:intl/intl.dart';
import 'package:open_file/open_file.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import '../../core/api/odoo_client.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/app_badge.dart';
import 'document_form_screen.dart';
import 'document_model.dart';
import 'document_service.dart';

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

  @override
  void didUpdateWidget(covariant DocumentsSection oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.owner.id != widget.owner.id ||
        oldWidget.owner.field != widget.owner.field) {
      _load();
    }
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final docs = await _service.list(widget.owner);
      if (mounted) setState(() => _docs = docs);
    } catch (_) {
      if (mounted) setState(() => _docs = []);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _openNewForm() async {
    final saved = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) =>
            DocumentFormScreen(odoo: widget.odoo, initialOwner: widget.owner),
      ),
    );
    if (saved == true && mounted) {
      _load();
    }
  }

  Future<void> _openEditForm(EstateDocument doc) async {
    final saved = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => DocumentFormScreen(odoo: widget.odoo, existing: doc),
      ),
    );
    if (saved == true && mounted) {
      _load();
    }
  }

  Future<void> _open(EstateDocument doc) async {
    if (doc.filename.isEmpty) {
      _showPendingDialog(doc);
      return;
    }

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
          : '${doc.name}.pdf';
      final file = File('${dir.path}/$safeName');
      await file.writeAsBytes(bytes);
      await OpenFile.open(file.path);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('No se pudo abrir el documento: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _openingId = null);
    }
  }

  Future<void> _download(EstateDocument doc) async {
    final messenger = ScaffoldMessenger.of(context);
    final colors = AppColors.of(context);
    messenger.showSnackBar(
      const SnackBar(
        content: Row(
          children: [
            SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: Colors.white,
              ),
            ),
            SizedBox(width: 12),
            Text('Descargando documento...'),
          ],
        ),
        duration: Duration(seconds: 20),
      ),
    );

    try {
      final bytes = await widget.odoo.downloadBytes(
        model: 'estate.document',
        id: doc.id,
        field: 'file',
      );
      final dir = await getTemporaryDirectory();
      final safeName = doc.filename.isNotEmpty
          ? doc.filename
          : '${doc.name}.pdf';
      final file = File('${dir.path}/$safeName');
      await file.writeAsBytes(bytes);

      bool savedToGallery = false;
      final isImage = doc.icon == Icons.image_outlined;
      if (isImage) {
        try {
          await Gal.putImage(file.path, album: 'Inmobi Documentos');
          savedToGallery = true;
        } catch (_) {}
      }

      messenger.hideCurrentSnackBar();
      if (!savedToGallery) {
        await OpenFile.open(file.path);
      }

      if (mounted) {
        messenger.showSnackBar(
          SnackBar(
            content: Text(
              savedToGallery
                  ? 'Imagen guardada en tu Galería (Inmobi Documentos).'
                  : 'Documento descargado: $safeName',
            ),
            action: SnackBarAction(
              label: savedToGallery ? 'Abrir Galería' : 'Compartir',
              textColor: Colors.white,
              onPressed: () {
                if (savedToGallery) {
                  Gal.open();
                } else {
                  Share.shareXFiles([XFile(file.path)]);
                }
              },
            ),
          ),
        );
      }
    } catch (e) {
      messenger.hideCurrentSnackBar();
      if (mounted) {
        messenger.showSnackBar(
          SnackBar(
            content: Text('No se pudo descargar el archivo: $e'),
            backgroundColor: colors.danger,
          ),
        );
      }
    }
  }

  Future<void> _share(EstateDocument doc) async {
    try {
      final bytes = await widget.odoo.downloadBytes(
        model: 'estate.document',
        id: doc.id,
        field: 'file',
      );
      final dir = await getTemporaryDirectory();
      final safeName = doc.filename.isNotEmpty
          ? doc.filename
          : '${doc.name}.pdf';
      final file = File('${dir.path}/$safeName');
      await file.writeAsBytes(bytes);

      await Share.shareXFiles([
        XFile(file.path),
      ], text: 'Documento: ${doc.name}');
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('No se pudo compartir el archivo: $e')),
        );
      }
    }
  }

  Future<void> _runAction(
    EstateDocument doc,
    String method,
    String okMsg,
  ) async {
    final messenger = ScaffoldMessenger.of(context);
    final colors = AppColors.of(context);
    try {
      await widget.odoo.callKw(
        model: 'estate.document',
        method: method,
        args: [
          [doc.id],
        ],
      );
      messenger.showSnackBar(
        SnackBar(content: Text(okMsg), backgroundColor: colors.success),
      );
      _load();
    } catch (e) {
      messenger.showSnackBar(
        SnackBar(
          content: const Text('Odoo rechazó la acción sobre el documento.'),
          backgroundColor: colors.danger,
        ),
      );
    }
  }

  void _showPendingDialog(EstateDocument doc) {
    final colors = AppColors.of(context);
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Row(
          children: [
            Icon(Icons.info_outline, color: colors.warning),
            const SizedBox(width: 8),
            const Text('Documento Pendiente', style: TextStyle(fontSize: 17)),
          ],
        ),
        content: Text(
          'El documento "${doc.name}" está registrado como pendiente y aún no tiene un archivo adjunto.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cerrar'),
          ),
          FilledButton.icon(
            onPressed: () {
              Navigator.pop(ctx);
              _openEditForm(doc);
            },
            icon: const Icon(Icons.upload_file_rounded, size: 16),
            label: const Text('Subir Archivo'),
          ),
        ],
      ),
    );
  }

  void _showActions(EstateDocument doc) {
    final colors = AppColors.of(context);
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => SafeArea(
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                margin: const EdgeInsets.symmetric(vertical: 10),
                width: 38,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.grey[300],
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 18,
                  vertical: 4,
                ),
                child: Row(
                  children: [
                    Icon(doc.icon, color: colors.navy, size: 28),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            doc.name,
                            style: const TextStyle(
                              fontWeight: FontWeight.w700,
                              fontSize: 15,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          Text(
                            doc.typeName.isNotEmpty
                                ? doc.typeName
                                : 'Documento Odoo',
                            style: TextStyle(color: colors.muted, fontSize: 12),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const Divider(height: 16),
              if (doc.filename.isNotEmpty) ...[
                ListTile(
                  leading: const Icon(
                    Icons.open_in_new_rounded,
                    color: Color(0xFF28235D),
                  ),
                  title: const Text('Abrir y Previsualizar'),
                  onTap: () {
                    Navigator.pop(ctx);
                    _open(doc);
                  },
                ),
                ListTile(
                  leading: const Icon(
                    Icons.download_rounded,
                    color: Color(0xFF10B981),
                  ),
                  title: const Text('Descargar a Galería / Archivos'),
                  onTap: () {
                    Navigator.pop(ctx);
                    _download(doc);
                  },
                ),
                ListTile(
                  leading: const Icon(
                    Icons.share_rounded,
                    color: Color(0xFF3B82F6),
                  ),
                  title: const Text('Compartir'),
                  onTap: () {
                    Navigator.pop(ctx);
                    _share(doc);
                  },
                ),
              ] else ...[
                ListTile(
                  leading: Icon(
                    Icons.upload_file_rounded,
                    color: colors.warning,
                  ),
                  title: const Text('Subir Archivo Pendiente'),
                  onTap: () {
                    Navigator.pop(ctx);
                    _openEditForm(doc);
                  },
                ),
              ],
              ListTile(
                leading: const Icon(
                  Icons.edit_outlined,
                  color: Color(0xFF4B5563),
                ),
                title: const Text('Editar Información del Documento'),
                onTap: () {
                  Navigator.pop(ctx);
                  _openEditForm(doc);
                },
              ),
              if (doc.state != 'verified')
                ListTile(
                  leading: Icon(Icons.verified_outlined, color: colors.success),
                  title: const Text('Marcar como Verificado'),
                  onTap: () {
                    Navigator.pop(ctx);
                    _runAction(
                      doc,
                      'action_verify',
                      'Documento verificado en Odoo.',
                    );
                  },
                ),
              if (doc.state != 'rejected')
                ListTile(
                  leading: Icon(Icons.cancel_outlined, color: colors.danger),
                  title: const Text('Rechazar Documento'),
                  onTap: () {
                    Navigator.pop(ctx);
                    _runAction(doc, 'action_reject', 'Documento rechazado.');
                  },
                ),
              const SizedBox(height: 8),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colors = AppColors.of(context);
    final dateFmt = DateFormat('d MMM y', 'es_EC');

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(
              'Documentos (${_docs.length})',
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
              onPressed: _openNewForm,
              icon: const Icon(Icons.add_rounded, size: 16),
              label: const Text(
                'Añadir documento',
                style: TextStyle(fontSize: 12.5),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        if (_loading)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 12),
            child: LinearProgressIndicator(),
          )
        else if (_docs.isEmpty)
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
                  Icons.folder_open_outlined,
                  size: 36,
                  color: colors.mutedLight,
                ),
                const SizedBox(height: 6),
                Text(
                  'Sin documentos cargados en esta propiedad.',
                  style: TextStyle(
                    fontSize: 13,
                    color: colors.muted,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(height: 10),
                OutlinedButton.icon(
                  onPressed: _openNewForm,
                  icon: const Icon(Icons.upload_file_rounded, size: 16),
                  label: const Text(
                    'Subir Primer Documento',
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
            itemCount: _docs.length,
            separatorBuilder: (_, _) => const SizedBox(height: 10),
            itemBuilder: (context, i) {
              final doc = _docs[i];
              final isOpening = _openingId == doc.id;
              final stateColor = DocumentStateStyle.color(doc.state, colors);

              return Container(
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF1E1A3E) : Colors.white,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: doc.state == 'rejected'
                        ? colors.danger.withValues(alpha: 0.5)
                        : (isDark ? Colors.white12 : colors.line),
                  ),
                ),
                child: Material(
                  color: Colors.transparent,
                  child: InkWell(
                    borderRadius: BorderRadius.circular(14),
                    onTap: isOpening ? null : () => _open(doc),
                    onLongPress: () => _showActions(doc),
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.all(8),
                                decoration: BoxDecoration(
                                  color: stateColor.withValues(alpha: 0.12),
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: isOpening
                                    ? SizedBox(
                                        width: 22,
                                        height: 22,
                                        child: CircularProgressIndicator(
                                          strokeWidth: 2,
                                          color: stateColor,
                                        ),
                                      )
                                    : Icon(
                                        doc.icon,
                                        color: stateColor,
                                        size: 22,
                                      ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      doc.name,
                                      style: const TextStyle(
                                        fontWeight: FontWeight.w700,
                                        fontSize: 14,
                                      ),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      doc.typeName.isNotEmpty
                                          ? '${doc.typeName}${doc.date != null ? " · ${dateFmt.format(doc.date!)}" : ""}'
                                          : (doc.date != null
                                                ? dateFmt.format(doc.date!)
                                                : ''),
                                      style: TextStyle(
                                        fontSize: 12,
                                        color: colors.muted,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(width: 8),
                              AppBadge(
                                label: DocumentStateStyle.label(doc.state),
                                color: stateColor,
                                background: stateColor.withValues(alpha: 0.12),
                              ),
                              IconButton(
                                icon: const Icon(
                                  Icons.more_vert_rounded,
                                  size: 20,
                                ),
                                onPressed: () => _showActions(doc),
                              ),
                            ],
                          ),
                          if (doc.confidentiality != 'internal' &&
                              doc.confidentiality.isNotEmpty) ...[
                            const SizedBox(height: 6),
                            Row(
                              children: [
                                AppBadge(
                                  icon: Icons.security_outlined,
                                  label: DocumentConfidentialityStyle.label(
                                    doc.confidentiality,
                                  ),
                                  color: DocumentConfidentialityStyle.color(
                                    doc.confidentiality,
                                    colors,
                                  ),
                                ),
                                if (doc.fileSizeMb > 0) ...[
                                  const SizedBox(width: 8),
                                  Text(
                                    '${doc.fileSizeMb.toStringAsFixed(2)} MB',
                                    style: TextStyle(
                                      fontSize: 11.5,
                                      color: colors.mutedLight,
                                    ),
                                  ),
                                ],
                              ],
                            ),
                          ],
                          if (doc.rejectionReason.isNotEmpty &&
                              doc.state == 'rejected') ...[
                            const SizedBox(height: 8),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 10,
                                vertical: 6,
                              ),
                              decoration: BoxDecoration(
                                color: colors.danger.withValues(alpha: 0.08),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Row(
                                children: [
                                  Icon(
                                    Icons.error_outline,
                                    size: 15,
                                    color: colors.danger,
                                  ),
                                  const SizedBox(width: 6),
                                  Expanded(
                                    child: Text(
                                      'Motivo de rechazo: ${doc.rejectionReason}',
                                      style: TextStyle(
                                        fontSize: 12,
                                        color: colors.danger,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                ),
              );
            },
          ),
      ],
    );
  }
}
