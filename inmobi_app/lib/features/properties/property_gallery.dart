import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:gal/gal.dart';
import 'package:open_file/open_file.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import '../../core/api/odoo_client.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/odoo_image.dart';

class _GalleryImage {
  final int id;
  final String name;
  const _GalleryImage(this.id, this.name);
}

class PropertyGallerySection extends StatefulWidget {
  final OdooClient odoo;
  final int propertyId;
  const PropertyGallerySection({
    super.key,
    required this.odoo,
    required this.propertyId,
  });

  @override
  State<PropertyGallerySection> createState() => _PropertyGallerySectionState();
}

class _PropertyGallerySectionState extends State<PropertyGallerySection> {
  List<_GalleryImage> _images = [];
  bool _loading = true;
  bool _uploading = false;
  bool _selectionMode = false;
  final Set<int> _selectedImageIds = {};
  bool _downloadingBatch = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final rows = await widget.odoo.searchRead(
        model: 'estate.property.image',
        domain: [
          ['property_id', '=', widget.propertyId],
        ],
        fields: ['name'],
        order: 'sequence, id',
      );
      if (mounted) {
        setState(
          () => _images = rows
              .map(
                (r) =>
                    _GalleryImage(r['id'] as int, (r['name'] ?? '').toString()),
              )
              .toList(),
        );
      }
    } catch (_) {
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _addPhotos() async {
    final picked = await FilePicker.platform.pickFiles(
      withData: true,
      allowMultiple: true,
      type: FileType.image,
    );
    if (picked == null || picked.files.isEmpty) return;
    setState(() => _uploading = true);
    try {
      for (final file in picked.files) {
        if (file.bytes == null) continue;
        await widget.odoo.create(
          model: 'estate.property.image',
          values: {
            'property_id': widget.propertyId,
            'image': base64Encode(file.bytes!),
          },
        );
      }
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No se pudieron subir algunas fotos.')),
        );
      }
    } finally {
      if (mounted) setState(() => _uploading = false);
    }
  }

  Future<void> _downloadBatch(Set<int> targetIds) async {
    if (targetIds.isEmpty) return;
    setState(() => _downloadingBatch = true);
    final messenger = ScaffoldMessenger.of(context);
    messenger.showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: Colors.white,
              ),
            ),
            const SizedBox(width: 12),
            Text(
              'Descargando ${targetIds.length} ${targetIds.length == 1 ? "foto" : "fotos"}...',
            ),
          ],
        ),
        duration: const Duration(seconds: 30),
      ),
    );

    try {
      final dir = await getTemporaryDirectory();
      final List<XFile> downloadedFiles = [];

      for (final id in targetIds) {
        final resp = await widget.odoo.client.get<List<int>>(
          '/web/image/estate.property.image/$id/image',
          options: Options(responseType: ResponseType.bytes),
        );
        final bytes = Uint8List.fromList(resp.data ?? const []);
        if (bytes.isNotEmpty) {
          final file = File(
            '${dir.path}/Propiedad_${widget.propertyId}_foto_$id.jpg',
          );
          await file.writeAsBytes(bytes);
          downloadedFiles.add(XFile(file.path));

          try {
            await Gal.putImage(file.path, album: 'Inmobi');
          } catch (_) {
            try {
              await Gal.putImage(file.path);
            } catch (_) {}
          }
        }
      }

      messenger.hideCurrentSnackBar();

      if (downloadedFiles.isNotEmpty) {
        if (mounted) {
          messenger.showSnackBar(
            SnackBar(
              content: Row(
                children: [
                  const Icon(
                    Icons.photo_library_rounded,
                    color: Colors.greenAccent,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      '${downloadedFiles.length} ${downloadedFiles.length == 1 ? "foto guardada" : "fotos guardadas"} en tu Galería (Inmobi).',
                    ),
                  ),
                ],
              ),
              action: SnackBarAction(
                label: 'Abrir Galería',
                textColor: Colors.white,
                onPressed: () => Gal.open(),
              ),
            ),
          );
          setState(() {
            _selectionMode = false;
            _selectedImageIds.clear();
          });
        }
      }
    } catch (e) {
      messenger.hideCurrentSnackBar();
      if (mounted) {
        messenger.showSnackBar(
          SnackBar(
            content: Text('Error al descargar fotos: $e'),
            backgroundColor: Colors.red[800],
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _downloadingBatch = false);
    }
  }

  void _openViewer(int startIndex) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => PropertyFullscreenViewer(
          odoo: widget.odoo,
          images: _images
              .map(
                (img) => (
                  model: 'estate.property.image',
                  id: img.id,
                  field: 'image',
                ),
              )
              .toList(),
          initialIndex: startIndex,
        ),
        fullscreenDialog: true,
      ),
    );
  }

  void _showDownloadOptions() {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 38,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.grey[300],
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              const SizedBox(height: 14),
              const Text(
                'Opciones de Descarga de Fotos',
                style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
              ),
              const SizedBox(height: 10),
              ListTile(
                leading: const Icon(
                  Icons.download_for_offline_rounded,
                  color: Color(0xFF10B981),
                ),
                title: Text('Descargar todas las fotos (${_images.length})'),
                subtitle: const Text(
                  'Descarga el paquete completo de la galería',
                ),
                onTap: () {
                  Navigator.pop(ctx);
                  _downloadBatch(_images.map((e) => e.id).toSet());
                },
              ),
              ListTile(
                leading: const Icon(
                  Icons.checklist_rounded,
                  color: Color(0xFF28235D),
                ),
                title: const Text('Seleccionar fotos específicas'),
                subtitle: const Text('Elige qué fotos descargar una por una'),
                onTap: () {
                  Navigator.pop(ctx);
                  setState(() {
                    _selectionMode = true;
                    _selectedImageIds.clear();
                  });
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(
              _selectionMode
                  ? '${_selectedImageIds.length} seleccionadas'
                  : 'Galería (${_images.length})',
              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
            ),
            const Spacer(),
            if (_images.isNotEmpty && !_selectionMode) ...[
              IconButton(
                tooltip: 'Opciones de descarga',
                icon: const Icon(Icons.download_rounded, size: 20),
                onPressed: _downloadingBatch ? null : _showDownloadOptions,
              ),
            ],
            if (_selectionMode) ...[
              TextButton(
                onPressed: () {
                  setState(() {
                    if (_selectedImageIds.length == _images.length) {
                      _selectedImageIds.clear();
                    } else {
                      _selectedImageIds.addAll(_images.map((e) => e.id));
                    }
                  });
                },
                child: Text(
                  _selectedImageIds.length == _images.length
                      ? 'Deseleccionar'
                      : 'Todas',
                  style: const TextStyle(fontSize: 12),
                ),
              ),
              TextButton(
                onPressed: () => setState(() {
                  _selectionMode = false;
                  _selectedImageIds.clear();
                }),
                child: const Text(
                  'Cancelar',
                  style: TextStyle(fontSize: 12, color: Colors.grey),
                ),
              ),
            ] else
              TextButton.icon(
                onPressed: _uploading ? null : _addPhotos,
                icon: _uploading
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.add_photo_alternate_outlined, size: 18),
                label: const Text('Añadir fotos'),
              ),
          ],
        ),
        if (_selectionMode && _images.isNotEmpty) ...[
          const SizedBox(height: 6),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              style: FilledButton.styleFrom(
                backgroundColor: const Color(0xFF10B981),
                padding: const EdgeInsets.symmetric(vertical: 10),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10),
                ),
              ),
              onPressed: _selectedImageIds.isEmpty || _downloadingBatch
                  ? null
                  : () => _downloadBatch(_selectedImageIds),
              icon: _downloadingBatch
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Icon(Icons.download_rounded, size: 18),
              label: Text(
                'Descargar ${_selectedImageIds.length} ${_selectedImageIds.length == 1 ? "foto seleccionada" : "fotos seleccionadas"}',
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
            ),
          ),
        ],
        const SizedBox(height: 8),
        if (_loading)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 12),
            child: LinearProgressIndicator(),
          )
        else if (_images.isEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 10),
            child: Text(
              'Sin fotos de galería todavía.',
              style: TextStyle(color: colors.mutedLight, fontSize: 13),
            ),
          )
        else
          GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: _images.length,
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 3,
              mainAxisSpacing: 8,
              crossAxisSpacing: 8,
            ),
            itemBuilder: (context, i) {
              final img = _images[i];
              final isSelected = _selectedImageIds.contains(img.id);

              return ClipRRect(
                borderRadius: BorderRadius.circular(10),
                child: Stack(
                  fit: StackFit.expand,
                  children: [
                    InkWell(
                      onTap: () {
                        if (_selectionMode) {
                          setState(() {
                            if (isSelected) {
                              _selectedImageIds.remove(img.id);
                            } else {
                              _selectedImageIds.add(img.id);
                            }
                          });
                        } else {
                          _openViewer(i);
                        }
                      },
                      onLongPress: () {
                        setState(() {
                          _selectionMode = true;
                          _selectedImageIds.add(img.id);
                        });
                      },
                      child: OdooImage(
                        odoo: widget.odoo,
                        model: 'estate.property.image',
                        id: img.id,
                        field: 'image',
                        width: 300,
                        height: 300,
                      ),
                    ),
                    if (_selectionMode)
                      Positioned(
                        top: 6,
                        right: 6,
                        child: Container(
                          decoration: BoxDecoration(
                            color: isSelected
                                ? const Color(0xFF10B981)
                                : Colors.black45,
                            shape: BoxShape.circle,
                            border: Border.all(color: Colors.white, width: 1.5),
                          ),
                          padding: const EdgeInsets.all(3),
                          child: Icon(
                            isSelected ? Icons.check : Icons.circle_outlined,
                            size: 14,
                            color: Colors.white,
                          ),
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

class PropertyFullscreenViewer extends StatefulWidget {
  final OdooClient odoo;
  final List<({String model, int id, String field})> images;
  final int initialIndex;

  const PropertyFullscreenViewer({
    super.key,
    required this.odoo,
    required this.images,
    this.initialIndex = 0,
  });

  @override
  State<PropertyFullscreenViewer> createState() =>
      _PropertyFullscreenViewerState();
}

class _PropertyFullscreenViewerState extends State<PropertyFullscreenViewer> {
  late final PageController _controller;
  late int _index;

  @override
  void initState() {
    super.initState();
    _index = widget.initialIndex;
    _controller = PageController(initialPage: _index);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _downloadCurrentImage() async {
    final img = widget.images[_index];
    final messenger = ScaffoldMessenger.of(context);
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
            Text('Descargando imagen en alta calidad...'),
          ],
        ),
        duration: Duration(seconds: 15),
      ),
    );

    try {
      final resp = await widget.odoo.client.get<List<int>>(
        '/web/image/${img.model}/${img.id}/${img.field}',
        options: Options(responseType: ResponseType.bytes),
      );
      final bytes = Uint8List.fromList(resp.data ?? const []);
      if (bytes.isEmpty) throw Exception('Imagen vacía');

      final dir = await getTemporaryDirectory();
      final fileName = 'Propiedad_${img.model}_${img.id}.jpg';
      final file = File('${dir.path}/$fileName');
      await file.writeAsBytes(bytes);

      bool savedToGallery = false;
      try {
        await Gal.putImage(file.path, album: 'Inmobi');
        savedToGallery = true;
      } catch (_) {
        try {
          await Gal.putImage(file.path);
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
            content: Row(
              children: [
                const Icon(
                  Icons.check_circle_rounded,
                  color: Colors.greenAccent,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    savedToGallery
                        ? 'Foto guardada en tu Galería (Álbum Inmobi).'
                        : 'Foto descargada en el dispositivo.',
                  ),
                ),
              ],
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
            content: Text('No se pudo descargar la imagen: $e'),
            backgroundColor: Colors.red[800],
          ),
        );
      }
    }
  }

  Future<void> _shareCurrentImage() async {
    final img = widget.images[_index];
    try {
      final resp = await widget.odoo.client.get<List<int>>(
        '/web/image/${img.model}/${img.id}/${img.field}',
        options: Options(responseType: ResponseType.bytes),
      );
      final bytes = Uint8List.fromList(resp.data ?? const []);
      if (bytes.isEmpty) throw Exception('Imagen vacía');

      final dir = await getTemporaryDirectory();
      final fileName = 'Propiedad_${img.model}_${img.id}.jpg';
      final file = File('${dir.path}/$fileName');
      await file.writeAsBytes(bytes);

      await Share.shareXFiles([
        XFile(file.path),
      ], text: 'Foto de propiedad Inmobi');
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('No se pudo compartir la imagen: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black.withValues(alpha: 0.85),
        foregroundColor: Colors.white,
        elevation: 0,
        title: Text(
          '${_index + 1} / ${widget.images.length}',
          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
        ),
        actions: [
          IconButton(
            tooltip: 'Descargar foto',
            icon: const Icon(Icons.download_rounded),
            onPressed: _downloadCurrentImage,
          ),
          IconButton(
            tooltip: 'Compartir',
            icon: const Icon(Icons.share_rounded),
            onPressed: _shareCurrentImage,
          ),
          IconButton(
            tooltip: 'Cerrar',
            icon: const Icon(Icons.close_rounded),
            onPressed: () => Navigator.of(context).pop(),
          ),
        ],
      ),
      body: PageView.builder(
        controller: _controller,
        itemCount: widget.images.length,
        onPageChanged: (i) => setState(() => _index = i),
        itemBuilder: (context, i) {
          final img = widget.images[i];
          return InteractiveViewer(
            minScale: 1,
            maxScale: 4.5,
            child: Center(
              child: OdooImage(
                odoo: widget.odoo,
                model: img.model,
                id: img.id,
                field: img.field,
                width: 1600,
                height: 1600,
                fit: BoxFit.contain,
                placeholderBuilder: (_) => const Center(
                  child: SizedBox(
                    width: 32,
                    height: 32,
                    child: CircularProgressIndicator(
                      color: Colors.white,
                      strokeWidth: 2,
                    ),
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
