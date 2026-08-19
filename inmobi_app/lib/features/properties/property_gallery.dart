import 'dart:convert';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../../core/api/odoo_client.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/odoo_image.dart';

class _GalleryImage {
  final int id;
  final String name;
  const _GalleryImage(this.id, this.name);
}

/// Galería completa de fotos de una propiedad (`estate.property.image`) — no
/// solo la imagen principal. Cuadrícula con miniaturas, toque para ver a
/// pantalla completa con zoom, y botón para subir más fotos desde el
/// dispositivo (se suben directo como nuevos registros de galería).
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
      // Silencioso: la sección queda vacía si falla.
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

  void _openViewer(int startIndex) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => _GalleryViewer(
          odoo: widget.odoo,
          images: _images,
          initialIndex: startIndex,
        ),
        fullscreenDialog: true,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(
              'Galería (${_images.length})',
              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
            ),
            const Spacer(),
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
        const SizedBox(height: 8),
        if (_loading)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 12),
            child: LinearProgressIndicator(),
          )
        else if (_images.isEmpty)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 10),
            child: Text(
              'Sin fotos de galería todavía.',
              style: TextStyle(color: AppColors.mutedLight, fontSize: 13),
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
              return ClipRRect(
                borderRadius: BorderRadius.circular(10),
                child: InkWell(
                  onTap: () => _openViewer(i),
                  child: OdooImage(
                    odoo: widget.odoo,
                    model: 'estate.property.image',
                    id: _images[i].id,
                    field: 'image',
                    width: 300,
                    height: 300,
                  ),
                ),
              );
            },
          ),
      ],
    );
  }
}

class _GalleryViewer extends StatefulWidget {
  final OdooClient odoo;
  final List<_GalleryImage> images;
  final int initialIndex;
  const _GalleryViewer({
    required this.odoo,
    required this.images,
    required this.initialIndex,
  });

  @override
  State<_GalleryViewer> createState() => _GalleryViewerState();
}

class _GalleryViewerState extends State<_GalleryViewer> {
  late final PageController _controller;
  late int _index;

  @override
  void initState() {
    super.initState();
    _index = widget.initialIndex;
    _controller = PageController(initialPage: _index);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        elevation: 0,
        title: Text('${_index + 1} / ${widget.images.length}'),
      ),
      body: PageView.builder(
        controller: _controller,
        itemCount: widget.images.length,
        onPageChanged: (i) => setState(() => _index = i),
        itemBuilder: (context, i) {
          return InteractiveViewer(
            minScale: 1,
            maxScale: 4,
            child: Center(
              child: OdooImage(
                odoo: widget.odoo,
                model: 'estate.property.image',
                id: widget.images[i].id,
                field: 'image',
                width: 1600,
                height: 1600,
                fit: BoxFit.contain,
                placeholderBuilder: (_) =>
                    const CircularProgressIndicator(color: Colors.white),
              ),
            ),
          );
        },
      ),
    );
  }
}
