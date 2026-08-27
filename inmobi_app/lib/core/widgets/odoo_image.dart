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

      // Odoo devuelve un SVG por defecto con la inicial cuando el usuario/registro
      // no tiene una foto real cargada. Flutter Image.memory no renderiza SVG crudo,
      // por lo que se detecta y se redirige al fallback con iniciales estilizadas.
      final ct = resp.headers.value('content-type') ?? '';
      final isSvg = ct.contains('svg') ||
          (bytes.length >= 4 &&
              ((bytes[0] == 60 && bytes[1] == 63) || // '<?'
                  (bytes[0] == 60 &&
                      bytes[1] == 115 &&
                      bytes[2] == 118 &&
                      bytes[3] == 103))); // '<svg'
      if (isSvg) {
        throw Exception('svg default placeholder');
      }

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
    return Image.memory(
      _bytes!,
      fit: widget.fit,
      gaplessPlayback: true,
      errorBuilder: (context, error, stackTrace) =>
          widget.errorBuilder?.call(context) ??
          Container(
            color: AppColors.navy.withValues(alpha: 0.07),
            child: const Icon(Icons.person_outline, color: AppColors.navy),
          ),
    );
  }
}

/// Avatar de usuario con imagen cargada desde Odoo (`res.users.avatar_128`)
/// y fallback automático a iniciales sobre círculo de color si no tiene foto.
class UserAvatar extends StatelessWidget {
  final OdooClient odoo;
  final int userId;
  final String userName;
  final double radius;
  final Color backgroundColor;

  const UserAvatar({
    super.key,
    required this.odoo,
    required this.userId,
    required this.userName,
    this.radius = 20,
    this.backgroundColor = const Color(0xFFD81F26),
  });

  @override
  Widget build(BuildContext context) {
    if (userId <= 0) {
      return _buildInitials();
    }
    final size = radius * 2;
    return ClipRRect(
      borderRadius: BorderRadius.circular(radius),
      child: SizedBox(
        width: size,
        height: size,
        child: OdooImage(
          odoo: odoo,
          model: 'res.users',
          id: userId,
          field: 'avatar_128',
          width: (size * 2).toInt(),
          height: (size * 2).toInt(),
          fit: BoxFit.cover,
          placeholderBuilder: (_) => _buildInitials(),
          errorBuilder: (_) => _buildInitials(),
        ),
      ),
    );
  }

  Widget _buildInitials() {
    final clean = userName.trim();
    final letter = clean.isNotEmpty ? clean[0].toUpperCase() : 'A';
    return Container(
      width: radius * 2,
      height: radius * 2,
      decoration: BoxDecoration(
        color: backgroundColor,
        shape: BoxShape.circle,
      ),
      alignment: Alignment.center,
      child: Text(
        letter,
        style: TextStyle(
          fontSize: radius * 0.78,
          fontWeight: FontWeight.w800,
          color: Colors.white,
        ),
      ),
    );
  }
}
