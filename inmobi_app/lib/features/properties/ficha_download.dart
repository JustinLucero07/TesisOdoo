import 'dart:io';

import 'package:flutter/material.dart';
import 'package:open_file/open_file.dart';
import 'package:path_provider/path_provider.dart';

import '../../core/api/odoo_client.dart';
import '../../core/theme/app_theme.dart';

/// Descarga la Ficha PDF de una propiedad usando el MISMO reporte QWeb del
/// ERP (`estate_reports.report_ficha_inmobi`), con los tres diseños y la
/// opción de incluir los datos del asesor — igual que el asistente del web.
class FichaDownloader {
  static const _reportName = 'estate_reports.report_ficha_inmobi';

  static const List<(String, String, String)> designs = [
    ('1', 'Portada vertical', 'Foto grande arriba con franja oscura'),
    ('2', 'Minimalista', 'Encabezado limpio y mosaico de fotos'),
    ('3', 'Portada a sangre', 'Foto de fondo a página completa'),
  ];

  /// Abre el selector de diseño y, al confirmar, genera y abre el PDF.
  static Future<void> start({
    required BuildContext context,
    required OdooClient odoo,
    required int propertyId,
    required String propertyTitle,
  }) async {
    final choice =
        await showModalBottomSheet<({String design, bool showContact})>(
          context: context,
          isScrollControlled: true,
          backgroundColor: AppColors.surface,
          shape: const RoundedRectangleBorder(
            borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
          ),
          builder: (_) => const _FichaOptionsSheet(),
        );
    if (choice == null || !context.mounted) return;

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
            Text('Generando ficha PDF...'),
          ],
        ),
        duration: Duration(seconds: 30),
      ),
    );

    try {
      final bytes = await odoo.downloadReportPdf(
        reportName: _reportName,
        id: propertyId,
        options: {
          'design': choice.design,
          'show_contact': choice.showContact,
          'property_id': propertyId,
        },
      );
      if (bytes.isEmpty) throw Exception('PDF vacío');

      final dir = await getTemporaryDirectory();
      // Nombre de archivo seguro: sin caracteres que rompan rutas.
      final safeTitle = propertyTitle
          .replaceAll(RegExp(r'[^\w\s-]'), '')
          .trim();
      final fileName =
          'Ficha_${safeTitle.isEmpty ? propertyId : safeTitle}.pdf';
      final file = File('${dir.path}/$fileName');
      await file.writeAsBytes(bytes);

      messenger.hideCurrentSnackBar();
      await OpenFile.open(file.path);
    } catch (e) {
      messenger.hideCurrentSnackBar();
      messenger.showSnackBar(
        const SnackBar(content: Text('No se pudo generar la ficha PDF.')),
      );
    }
  }
}

class _FichaOptionsSheet extends StatefulWidget {
  const _FichaOptionsSheet();

  @override
  State<_FichaOptionsSheet> createState() => _FichaOptionsSheetState();
}

class _FichaOptionsSheetState extends State<_FichaOptionsSheet> {
  String _design = '1';
  bool _showContact = true;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 20),
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
              'Descargar Ficha PDF',
              style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 4),
            const Text(
              'Elige el diseño de la ficha comercial.',
              style: TextStyle(fontSize: 13, color: AppColors.muted),
            ),
            const SizedBox(height: 16),
            ...FichaDownloader.designs.map((d) {
              final (value, title, subtitle) = d;
              final selected = _design == value;
              return Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: InkWell(
                  borderRadius: BorderRadius.circular(12),
                  onTap: () => setState(() => _design = value),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 180),
                    padding: const EdgeInsets.all(13),
                    decoration: BoxDecoration(
                      color: selected
                          ? AppColors.navy.withValues(alpha: 0.06)
                          : AppColors.neutralBg,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: selected ? AppColors.navy : Colors.transparent,
                        width: 1.5,
                      ),
                    ),
                    child: Row(
                      children: [
                        Icon(
                          selected
                              ? Icons.radio_button_checked
                              : Icons.radio_button_unchecked,
                          size: 20,
                          color: selected
                              ? AppColors.navy
                              : AppColors.mutedLight,
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                title,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w600,
                                  fontSize: 14,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                subtitle,
                                style: const TextStyle(
                                  fontSize: 11.5,
                                  color: AppColors.mutedLight,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            }),
            const SizedBox(height: 4),
            SwitchListTile.adaptive(
              contentPadding: EdgeInsets.zero,
              title: const Text(
                'Incluir datos del asesor',
                style: TextStyle(fontSize: 14),
              ),
              value: _showContact,
              onChanged: (v) => setState(() => _showContact = v),
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: () => Navigator.of(
                  context,
                ).pop((design: _design, showContact: _showContact)),
                icon: const Icon(Icons.download, size: 18),
                label: const Text('Generar PDF'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
