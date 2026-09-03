import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api/odoo_client.dart';
import '../../core/config.dart';
import '../../core/theme/app_theme.dart';
import 'property_model.dart';

class WordpressSection extends StatefulWidget {
  final OdooClient odoo;
  final Property property;
  final VoidCallback onChanged;

  const WordpressSection({
    super.key,
    required this.odoo,
    required this.property,
    required this.onChanged,
  });

  @override
  State<WordpressSection> createState() => _WordpressSectionState();
}

class _WordpressSectionState extends State<WordpressSection> {
  bool _busy = false;

  Future<void> _publish() async {
    final messenger = ScaffoldMessenger.of(context);
    setState(() => _busy = true);
    messenger.showSnackBar(
      const SnackBar(
        content: Text('Publicando en el sitio… puede tardar según las fotos.'),
        duration: Duration(seconds: 20),
      ),
    );
    try {
      final ok = await widget.odoo.callKw(
        model: 'estate.property',
        method: '_wp_sync_now',
        args: [
          [widget.property.id],
        ],
      );
      messenger.hideCurrentSnackBar();
      messenger.showSnackBar(
        SnackBar(
          content: Text(
            ok == true
                ? 'Propiedad publicada en el sitio web.'
                : 'No se publicó: revisa la configuración de WordPress en el ERP.',
          ),
        ),
      );
      widget.onChanged();
    } catch (e) {
      messenger.hideCurrentSnackBar();
      messenger.showSnackBar(
        const SnackBar(
          content: Text(
            'No se pudo publicar. Revisa la conexión con WordPress en el ERP.',
          ),
        ),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _unpublish() async {
    final p = AppColors.of(context);
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Quitar del sitio web'),
        content: const Text(
          'La propiedad dejará de verse en el sitio público. '
          'Podrás volver a publicarla cuando quieras.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            style: FilledButton.styleFrom(backgroundColor: p.danger),
            child: const Text('Quitar'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    final messenger = ScaffoldMessenger.of(context);
    setState(() => _busy = true);
    try {
      await widget.odoo.callKw(
        model: 'estate.property',
        method: 'action_unpublish_wp',
        args: [
          [widget.property.id],
        ],
      );
      messenger.showSnackBar(
        const SnackBar(content: Text('Propiedad quitada del sitio web.')),
      );
      widget.onChanged();
    } catch (e) {
      messenger.showSnackBar(
        const SnackBar(content: Text('No se pudo quitar del sitio web.')),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _openInSite() async {
    final uri = Uri.parse(
      '${AppConfig.wordpressSite}/?p=${widget.property.wpPostId}',
    );
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = AppColors.of(context);
    final prop = widget.property;
    final published = prop.wpPublished;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(AppSpace.lg),
          decoration: BoxDecoration(
            color: published
                ? p.success.withValues(alpha: p.isDark ? 0.14 : 0.07)
                : p.surfaceAlt,
            borderRadius: BorderRadius.circular(AppRadius.md),
            border: Border.all(
              color: published ? p.success.withValues(alpha: 0.3) : p.line,
            ),
          ),
          child: Row(
            children: [
              Icon(
                published ? Icons.public : Icons.public_off,
                size: 22,
                color: published ? p.success : p.mutedLight,
              ),
              const SizedBox(width: AppSpace.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      published ? 'Publicada en el sitio' : 'No publicada',
                      style: AppType.body.copyWith(
                        fontWeight: FontWeight.w600,
                        color: published ? p.success : p.ink,
                      ),
                    ),
                    const SizedBox(height: 1),
                    Text(
                      published
                          ? (prop.wpNeedsSync
                                ? 'Tiene cambios sin sincronizar'
                                : 'Visible para el público')
                          : 'Solo visible dentro del ERP',
                      style: AppType.caption.copyWith(
                        color: prop.wpNeedsSync && published
                            ? p.warning
                            : p.muted,
                      ),
                    ),
                  ],
                ),
              ),
              if (_busy)
                const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
            ],
          ),
        ),
        const SizedBox(height: AppSpace.md),
        if (!published)
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _busy ? null : _publish,
              icon: const Icon(Icons.cloud_upload_outlined, size: 18),
              label: const Text('Publicar en el sitio web'),
            ),
          )
        else ...[
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _busy ? null : _publish,
                  icon: const Icon(Icons.sync, size: 17),
                  label: Text(
                    prop.wpNeedsSync
                        ? 'Sincronizar cambios'
                        : 'Volver a publicar',
                  ),
                ),
              ),
              if (prop.wpPostId > 0) ...[
                const SizedBox(width: AppSpace.sm),
                OutlinedButton(
                  onPressed: _busy ? null : _openInSite,
                  child: const Icon(Icons.open_in_new, size: 17),
                ),
              ],
            ],
          ),
          const SizedBox(height: AppSpace.sm),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: _busy ? null : _unpublish,
              style: OutlinedButton.styleFrom(
                foregroundColor: p.danger,
                side: BorderSide(color: p.danger.withValues(alpha: 0.5)),
              ),
              icon: const Icon(Icons.public_off, size: 17),
              label: const Text('Quitar del sitio web'),
            ),
          ),
        ],
      ],
    );
  }
}
