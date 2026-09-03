import 'dart:convert';
import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:open_file/open_file.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api/odoo_client.dart';
import '../../core/theme/app_theme.dart';
import 'property_model.dart';

enum FichaActionType { open, sharePdf, shareWhatsappText }

/// Manejo de la Ficha PDF y Ficha Comercial de una propiedad.
/// Permite descargar, previsualizar y compartir la ficha en formato PDF
/// o como mensaje enriquecido para WhatsApp.
class FichaDownloader {
  static const _reportName = 'estate_reports.report_ficha_inmobi';

  static const List<(String, String, String)> designs = [
    ('1', 'Portada vertical', 'Foto grande arriba con franja oscura'),
    ('2', 'Minimalista', 'Encabezado limpio y mosaico de fotos'),
    ('3', 'Portada a sangre', 'Foto de fondo a página completa'),
  ];

  /// Descarga y abre la Hoja de Captación subida (archivo del cliente) o genera la plantilla oficial PDF
  static Future<void> openCaptureSheet({
    required BuildContext context,
    required OdooClient odoo,
    required Property property,
  }) async {
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
            Text('Abriendo Hoja de Captación...'),
          ],
        ),
        duration: Duration(seconds: 30),
      ),
    );

    try {
      // 1. Primero intentar cargar el archivo subido en el campo capture_sheet de Odoo
      final rows = await odoo.searchRead(
        model: 'estate.property',
        domain: [
          ['id', '=', property.id],
        ],
        fields: ['capture_sheet', 'capture_sheet_filename'],
        limit: 1,
      );

      List<int> bytes = [];
      String fileName = 'Hoja_Captacion_${property.id}.pdf';

      if (rows.isNotEmpty &&
          rows.first['capture_sheet'] != null &&
          rows.first['capture_sheet'] != false &&
          rows.first['capture_sheet'].toString().isNotEmpty) {
        final b64 = rows.first['capture_sheet'].toString();
        bytes = base64Decode(b64);
        final rawFn = rows.first['capture_sheet_filename']?.toString();
        if (rawFn != null && rawFn.isNotEmpty && rawFn != 'false') {
          fileName = rawFn;
        }
      } else {
        // 2. Si no hay archivo subido, generar el reporte QWeb estándar de Odoo
        bytes = await odoo.downloadReportPdf(
          reportName: 'estate_management.report_capture_sheet_template',
          id: property.id,
        );
        final title = property.title.isEmpty ? property.reference : property.title;
        final safeTitle = title.replaceAll(RegExp(r'[^\w\s-]'), '').trim();
        fileName = 'Captacion_${safeTitle.isEmpty ? property.id : safeTitle}.pdf';
      }

      if (bytes.isEmpty) throw Exception('No se pudo obtener el archivo.');

      final dir = await getTemporaryDirectory();
      final file = File('${dir.path}/$fileName');
      await file.writeAsBytes(bytes);

      messenger.hideCurrentSnackBar();
      await OpenFile.open(file.path);
    } catch (e) {
      messenger.hideCurrentSnackBar();
      messenger.showSnackBar(
        SnackBar(
          content: Text('No se pudo abrir la Hoja de Captación: $e'),
          backgroundColor: Colors.red[800],
        ),
      );
    }
  }

  /// Sube o reemplaza la Hoja de Captación desde el celular
  static Future<bool> uploadCaptureSheet({
    required BuildContext context,
    required OdooClient odoo,
    required int propertyId,
  }) async {
    try {
      final res = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['pdf', 'png', 'jpg', 'jpeg', 'webp'],
        withData: true,
      );
      if (res == null || res.files.isEmpty) return false;

      final file = res.files.first;
      final bytes = file.bytes ?? (file.path != null ? await File(file.path!).readAsBytes() : null);
      if (bytes == null || bytes.isEmpty) throw Exception('Archivo vacío');

      final b64 = base64Encode(bytes);
      await odoo.write(
        model: 'estate.property',
        id: propertyId,
        values: {
          'capture_sheet': b64,
          'capture_sheet_filename': file.name,
        },
      );

      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Hoja de captación "${file.name}" subida exitosamente.')),
        );
      }
      return true;
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('No se pudo subir el archivo: $e'), backgroundColor: Colors.red[800]),
        );
      }
      return false;
    }
  }

  /// Elimina la Hoja de Captación subida en Odoo
  static Future<bool> deleteCaptureSheet({
    required BuildContext context,
    required OdooClient odoo,
    required int propertyId,
  }) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('¿Eliminar Hoja de Captación?'),
        content: const Text('Se quitará el archivo adjunto de la propiedad en Odoo.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: const Color(0xFFD81F26)),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Eliminar'),
          ),
        ],
      ),
    );
    if (confirm != true) return false;

    try {
      await odoo.write(
        model: 'estate.property',
        id: propertyId,
        values: {
          'capture_sheet': false,
          'capture_sheet_filename': false,
        },
      );
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Hoja de captación eliminada.')),
        );
      }
      return true;
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No se pudo eliminar el archivo adjunto.')),
        );
      }
      return false;
    }
  }

  /// Abre el modal de opciones de ficha comercial
  static Future<void> start({
    required BuildContext context,
    required OdooClient odoo,
    required Property property,
  }) async {
    final choice = await showModalBottomSheet<({
      String design,
      bool showContact,
      FichaActionType action,
    })>(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.of(context).surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => _FichaOptionsSheet(property: property),
    );

    if (choice == null || !context.mounted) return;

    if (choice.action == FichaActionType.shareWhatsappText) {
      await shareCommercialWhatsapp(property: property);
      return;
    }

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
        id: property.id,
        options: {
          'design': choice.design,
          'show_contact': choice.showContact,
          'property_id': property.id,
        },
      );

      if (bytes.isEmpty) throw Exception('PDF vacío');

      final dir = await getTemporaryDirectory();
      final title = property.title.isEmpty ? property.reference : property.title;
      final safeTitle = title.replaceAll(RegExp(r'[^\w\s-]'), '').trim();
      final fileName = 'Ficha_${safeTitle.isEmpty ? property.id : safeTitle}.pdf';
      final file = File('${dir.path}/$fileName');
      await file.writeAsBytes(bytes);

      messenger.hideCurrentSnackBar();

      if (choice.action == FichaActionType.sharePdf) {
        await Share.shareXFiles(
          [XFile(file.path)],
          text: 'Ficha Comercial: $title\nPrecio: \$${property.displayPrice.toStringAsFixed(0)}',
        );
      } else {
        await OpenFile.open(file.path);
      }
    } catch (e) {
      messenger.hideCurrentSnackBar();
      messenger.showSnackBar(
        const SnackBar(content: Text('No se pudo generar o compartir la ficha PDF.')),
      );
    }
  }

  /// Construye y envía un mensaje formateado por WhatsApp o selector nativo
  static Future<void> shareCommercialWhatsapp({
    required Property property,
    String? phone,
  }) async {
    final title = property.title.isEmpty ? property.reference : property.title;
    final location = [property.sector, property.city].where((s) => s.isNotEmpty).join(', ');
    final operation = property.isForSale ? 'VENTA' : 'ARRIENDO';

    final buffer = StringBuffer();
    buffer.writeln('✨ *OPORTUNIDAD INMOBILIARIA - $operation* ✨');
    buffer.writeln('🏢 *$title*');
    if (location.isNotEmpty) buffer.writeln('📍 *Ubicación:* $location');
    buffer.writeln('💰 *Precio:* \$${property.displayPrice.toStringAsFixed(0)}');
    buffer.writeln('📐 *Área:* ${property.area.toStringAsFixed(0)} m²');
    buffer.writeln('🛏️ *Habitaciones:* ${property.bedrooms} | 🚿 *Baños:* ${property.bathrooms.toStringAsFixed(0)}');
    if (property.parkingSpaces > 0) {
      buffer.writeln('🚗 *Parqueaderos:* ${property.parkingSpaces}');
    }

    if (property.wpUrl.isNotEmpty) {
      buffer.writeln('\n🔗 *Ver detalles y fotos online:* ${property.wpUrl}');
    }

    buffer.writeln('\n📲 *Contáctanos para más información o coordinar una visita.*');

    final message = buffer.toString();

    if (phone != null && phone.isNotEmpty) {
      final digits = phone.replaceAll(RegExp(r'[^0-9]'), '');
      final uri = Uri.parse('https://wa.me/$digits?text=${Uri.encodeComponent(message)}');
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
        return;
      }
    }

    await Share.share(message, subject: 'Ficha Comercial: $title');
  }
}

class _FichaOptionsSheet extends StatefulWidget {
  final Property property;
  const _FichaOptionsSheet({required this.property});

  @override
  State<_FichaOptionsSheet> createState() => _FichaOptionsSheetState();
}

class _FichaOptionsSheetState extends State<_FichaOptionsSheet> {
  String _design = '1';
  bool _showContact = true;

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.of(context);
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 14, 20, 20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 42,
                height: 4.5,
                decoration: BoxDecoration(
                  color: colors.line,
                  borderRadius: BorderRadius.circular(3),
                ),
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: colors.navy.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(Icons.share_rounded, color: colors.navy, size: 22),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Ficha Comercial y Compartir',
                        style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
                      ),
                      Text(
                        'Elige el formato y diseño para compartir',
                        style: TextStyle(fontSize: 12.5, color: colors.muted),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Text(
              'DISEÑO DEL PDF',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w700,
                color: colors.mutedLight,
                letterSpacing: 0.8,
              ),
            ),
            const SizedBox(height: 8),
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
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
                    decoration: BoxDecoration(
                      color: selected
                          ? colors.navy.withValues(alpha: 0.07)
                          : colors.neutralBg,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: selected ? colors.navy : Colors.transparent,
                        width: 1.5,
                      ),
                    ),
                    child: Row(
                      children: [
                        Icon(
                          selected
                              ? Icons.radio_button_checked
                              : Icons.radio_button_unchecked,
                          size: 19,
                          color: selected ? colors.navy : colors.mutedLight,
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                title,
                                style: TextStyle(
                                  fontWeight: FontWeight.w600,
                                  fontSize: 13.5,
                                  color: selected ? colors.navy : colors.ink,
                                ),
                              ),
                              Text(
                                subtitle,
                                style: TextStyle(
                                  fontSize: 11.5,
                                  color: colors.mutedLight,
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
            SwitchListTile.adaptive(
              contentPadding: EdgeInsets.zero,
              title: const Text(
                'Incluir datos del asesor comercial',
                style: TextStyle(fontSize: 13.5, fontWeight: FontWeight.w500),
              ),
              value: _showContact,
              onChanged: (v) => setState(() => _showContact = v),
            ),
            const SizedBox(height: 12),

            // Acciones principales
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => Navigator.of(context).pop((
                      design: _design,
                      showContact: _showContact,
                      action: FichaActionType.open,
                    )),
                    icon: const Icon(Icons.visibility_outlined, size: 18),
                    label: const Text('Ver PDF'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => Navigator.of(context).pop((
                      design: _design,
                      showContact: _showContact,
                      action: FichaActionType.sharePdf,
                    )),
                    icon: const Icon(Icons.share_outlined, size: 18),
                    label: const Text('Compartir PDF'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: () => Navigator.of(context).pop((
                  design: _design,
                  showContact: _showContact,
                  action: FichaActionType.shareWhatsappText,
                )),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF25D366),
                  foregroundColor: Colors.white,
                ),
                icon: const Icon(Icons.chat_outlined, size: 18),
                label: const Text('Compartir texto por WhatsApp'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
