import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import '../api/odoo_client.dart';
import '../theme/app_theme.dart';

/// Imagen de un registro de Odoo (ej. `estate.property.image_main`), cargada
/// perezosamente y REDIMENSIONADA POR EL SERVIDOR vía el endpoint nativo
/// `/web/image/<model>/<id>/<field>/<width>x<height>` — el mismo que usa el
/// cliente web de Odoo. Así cada fila de una lista pide solo una miniatura
/// pequeña en vez de la foto completa en base64 embebida en el JSON del
/// listado, que es lo que colgaba la app con catálogos grandes.
///
/// Se cachea en memoria por (model, id, field, size) durante la sesión, para
/// no re-descargar la misma miniatura al hacer scroll hacia arriba y abajo.
class OdooImage extends StatefulWidget {
  final OdooClient odoo;
  final String model;
  final int id;
  final String field;
  final int width;
  final int height;
  final BoxFit fit;
  final Widget Function(BuildContext context)? placeholderBuilder;
  final Widget Function(BuildContext context)? errorBuilder;

  const OdooImage({
    super.key,
    required this.odoo,
    required this.model,
    required this.id,
    required this.field,
    this.width = 128,
    this.height = 128,
    this.fit = BoxFit.cover,
    this.placeholderBuilder,
    this.errorBuilder,
  });

  static final Map<String, Uint8List> _cache = {};

  String get _cacheKey => '$model/$id/$field/${width}x$height';

  @override
  State<OdooImage> createState() => _OdooImageState();
}

class _OdooImageState extends State<OdooImage> {
  Uint8List? _bytes;
  bool _loading = true;
  bool _failed = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(covariant OdooImage old) {
    super.didUpdateWidget(old);
    if (old._cacheKey != widget._cacheKey) _load();
  }

  Future<void> _load() async {
    final cached = OdooImage._cache[widget._cacheKey];
    if (cached != null) {
      setState(() {
        _bytes = cached;
        _loading = false;
      });
      return;
    }
    setState(() {
      _loading = true;
      _failed = false;
    });
    try {
      final resp = await widget.odoo.client.get<List<int>>(
        '/web/image/${widget.model}/${widget.id}/${widget.field}/${widget.width}x${widget.height}',
        options: Options(responseType: ResponseType.bytes),
      );
      final bytes = Uint8List.fromList(resp.data ?? const []);
      if (bytes.isEmpty) throw Exception('empty image');
      OdooImage._cache[widget._cacheKey] = bytes;
      if (!mounted) return;
      setState(() {
        _bytes = bytes;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _failed = true;
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return widget.placeholderBuilder?.call(context) ??
          Container(color: AppColors.neutralBg);
    }
    if (_failed || _bytes == null) {
      return widget.errorBuilder?.call(context) ??
          Container(
            color: AppColors.navy.withValues(alpha: 0.07),
            child: const Icon(Icons.home_outlined, color: AppColors.navy),
          );
    }
    return Image.memory(_bytes!, fit: widget.fit, gaplessPlayback: true);
  }
}
