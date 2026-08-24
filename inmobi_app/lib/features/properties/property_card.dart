import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api/odoo_client.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/odoo_image.dart';
import '../visits/visit_form_screen.dart';
import 'ficha_download.dart';
import 'property_detail_screen.dart';
import 'property_form_screen.dart';
import 'property_model.dart';

/// Tarjeta de propiedad premium con galería de fotos inmersiva, badges frosted glass,
/// precio destacado con cálculo por m² y botones de acción rápida comercial.
class PropertyCard extends StatefulWidget {
  final Property property;
  final OdooClient odoo;
  final NumberFormat currency;

  const PropertyCard({
    super.key,
    required this.property,
    required this.odoo,
    required this.currency,
  });

  @override
  State<PropertyCard> createState() => _PropertyCardState();
}

class _PropertyCardState extends State<PropertyCard> {
  bool _expanded = false;
  final _pageController = PageController();
  int _photoIndex = 0;

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  void _openQuickActions() {
    HapticFeedback.mediumImpact();
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (_) => _PropertyQuickActionSheet(
        property: widget.property,
        odoo: widget.odoo,
        currency: widget.currency,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.property;
    final photoCount = p.imageIds.isEmpty ? 1 : p.imageIds.length;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final pricePerM2 = (p.area > 0 && p.displayPrice > 0)
        ? (p.displayPrice / p.area)
        : null;

    return Container(
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1E1A3E) : Colors.white,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(
          color: isDark
              ? Colors.white.withValues(alpha: 0.08)
              : AppColors.line.withValues(alpha: 0.8),
        ),
        boxShadow: softShadow(opacity: isDark ? 0.25 : 0.05, isDark: isDark),
      ),
      clipBehavior: Clip.antiAlias,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () => Navigator.of(context).push(
            MaterialPageRoute(
              builder: (_) => PropertyDetailScreen(propertyId: p.id),
            ),
          ),
          onLongPress: _openQuickActions,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Galería de fotos e indicadores flotantes
              Stack(
                children: [
                  AspectRatio(
                    aspectRatio: 16 / 10,
                    child: photoCount == 1
                        ? OdooImage(
                            odoo: widget.odoo,
                            model: 'estate.property',
                            id: p.id,
                            field: 'image_main',
                            width: 640,
                            height: 400,
                            errorBuilder: (_) => Container(
                              color: AppColors.navy.withValues(alpha: 0.07),
                              child: const Icon(
                                Icons.home_work_outlined,
                                size: 44,
                                color: AppColors.navy,
                              ),
                            ),
                          )
                        : PageView.builder(
                            controller: _pageController,
                            itemCount: p.imageIds.length,
                            onPageChanged: (i) =>
                                setState(() => _photoIndex = i),
                            itemBuilder: (context, i) => OdooImage(
                              odoo: widget.odoo,
                              model: 'estate.property.image',
                              id: p.imageIds[i],
                              field: 'image',
                              width: 640,
                              height: 400,
                              errorBuilder: (_) => Container(
                                color: AppColors.navy.withValues(alpha: 0.07),
                                child: const Icon(
                                  Icons.home_work_outlined,
                                  size: 44,
                                  color: AppColors.navy,
                                ),
                              ),
                            ),
                          ),
                  ),

                  // Gradiente inferior sutil sobre la foto
                  Positioned(
                    bottom: 0,
                    left: 0,
                    right: 0,
                    height: 50,
                    child: Container(
                      decoration: const BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                          colors: [
                            Colors.transparent,
                            Color(0x66000000),
                          ],
                        ),
                      ),
                    ),
                  ),

                  // Píldoras de fotos & Indicador numérico
                  if (photoCount > 1) ...[
                    Positioned(
                      bottom: 12,
                      left: 0,
                      right: 0,
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: List.generate(
                          photoCount,
                          (i) => AnimatedContainer(
                            duration: const Duration(milliseconds: 200),
                            margin: const EdgeInsets.symmetric(horizontal: 2.5),
                            width: i == _photoIndex ? 16 : 5,
                            height: 5,
                            decoration: BoxDecoration(
                              color: Colors.white.withValues(
                                alpha: i == _photoIndex ? 0.95 : 0.45,
                              ),
                              borderRadius: BorderRadius.circular(3),
                            ),
                          ),
                        ),
                      ),
                    ),
                    Positioned(
                      bottom: 10,
                      right: 12,
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(10),
                        child: BackdropFilter(
                          filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 3,
                            ),
                            decoration: BoxDecoration(
                              color: Colors.black.withValues(alpha: 0.45),
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(
                                color: Colors.white.withValues(alpha: 0.15),
                                width: 0.8,
                              ),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                const Icon(
                                  Icons.photo_camera_rounded,
                                  size: 11,
                                  color: Colors.white,
                                ),
                                const SizedBox(width: 4),
                                Text(
                                  '${_photoIndex + 1}/$photoCount',
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontSize: 10.5,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],

                  // Badges superiores con Glassmorphism
                  if (p.isExclusive)
                    Positioned(
                      top: 12,
                      left: 12,
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(20),
                        child: BackdropFilter(
                          filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                            decoration: BoxDecoration(
                              color: const Color(0xFFD81F26).withValues(alpha: 0.9),
                              borderRadius: BorderRadius.circular(20),
                              border: Border.all(color: Colors.white24, width: 0.8),
                            ),
                            child: const Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(Icons.star_rounded, size: 12, color: Colors.white),
                                SizedBox(width: 4),
                                Text(
                                  'Exclusiva',
                                  style: TextStyle(
                                    color: Colors.white,
                                    fontSize: 11,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                  Positioned(
                    top: 12,
                    right: 12,
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(20),
                      child: BackdropFilter(
                        filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                          decoration: BoxDecoration(
                            color: PropertyStateLabel.color(p.state).withValues(alpha: 0.9),
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(color: Colors.white24, width: 0.8),
                          ),
                          child: Text(
                            PropertyStateLabel.label(p.state),
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),

              // Contenido descriptivo
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Fila de Precio y Métrica de m²
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.baseline,
                      textBaseline: TextBaseline.alphabetic,
                      children: [
                        Text(
                          widget.currency.format(p.displayPrice),
                          style: TextStyle(
                            fontWeight: FontWeight.w800,
                            color: isDark ? AppColors.navyLight : AppColors.navy,
                            fontSize: 20,
                            letterSpacing: -0.5,
                          ),
                        ),
                        if (pricePerM2 != null) ...[
                          const SizedBox(width: 8),
                          Text(
                            '•  ${widget.currency.format(pricePerM2)}/m²',
                            style: const TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                              color: AppColors.mutedLight,
                            ),
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: 6),

                    // Título de la propiedad
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          child: Text(
                            p.title.isEmpty ? p.reference : p.title,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontWeight: FontWeight.w700,
                              fontSize: 15.5,
                              color: isDark ? Colors.white : AppColors.ink,
                              letterSpacing: -0.2,
                            ),
                          ),
                        ),
                        if (p.description.isNotEmpty)
                          _ExpandButton(
                            expanded: _expanded,
                            onTap: () => setState(() => _expanded = !_expanded),
                          ),
                      ],
                    ),
                    const SizedBox(height: 4),

                    // Ubicación
                    Row(
                      children: [
                        const Icon(
                          Icons.location_on_outlined,
                          size: 14,
                          color: AppColors.mutedLight,
                        ),
                        const SizedBox(width: 4),
                        Expanded(
                          child: Text(
                            [
                              if (p.sector.isNotEmpty) p.sector,
                              if (p.city.isNotEmpty) p.city,
                            ].join(', '),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: AppColors.muted,
                              fontSize: 12.5,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),

                    // Chips de Especificaciones (Área, Habitaciones, Baños, Parqueos)
                    SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: Row(
                        children: [
                          if (p.area > 0) ...[
                            _SpecChip(
                              icon: Icons.square_foot_rounded,
                              label: '${p.area.toStringAsFixed(0)} m²',
                              isDark: isDark,
                            ),
                            const SizedBox(width: 6),
                          ],
                          if (p.bedrooms > 0) ...[
                            _SpecChip(
                              icon: Icons.bed_rounded,
                              label: '${p.bedrooms} hab.',
                              isDark: isDark,
                            ),
                            const SizedBox(width: 6),
                          ],
                          if (p.bathrooms > 0) ...[
                            _SpecChip(
                              icon: Icons.bathtub_rounded,
                              label: '${p.bathrooms.toStringAsFixed(0)} bñ.',
                              isDark: isDark,
                            ),
                            const SizedBox(width: 6),
                          ],
                          if (p.parkingSpaces > 0)
                            _SpecChip(
                              icon: Icons.directions_car_rounded,
                              label: '${p.parkingSpaces} est.',
                              isDark: isDark,
                            ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 12),

                    // Fila de Acciones Comerciales
                    Row(
                      children: [
                        // Botón Compartir Ficha
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: () => FichaDownloader.start(
                              context: context,
                              odoo: widget.odoo,
                              property: p,
                            ),
                            style: OutlinedButton.styleFrom(
                              padding: const EdgeInsets.symmetric(vertical: 9, horizontal: 4),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                              side: BorderSide(
                                color: isDark
                                    ? Colors.white.withValues(alpha: 0.15)
                                    : AppColors.line,
                              ),
                            ),
                            icon: const Icon(Icons.share_outlined, size: 15),
                            label: const FittedBox(
                              fit: BoxFit.scaleDown,
                              child: Text(
                                'Ficha PDF',
                                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        // Botón WhatsApp Comercial
                        Expanded(
                          child: ElevatedButton.icon(
                            onPressed: () => FichaDownloader.shareCommercialWhatsapp(
                              property: p,
                            ),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: const Color(0xFF25D366),
                              foregroundColor: Colors.white,
                              padding: const EdgeInsets.symmetric(vertical: 9, horizontal: 4),
                              elevation: 0,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                            ),
                            icon: const Icon(Icons.chat_bubble_outline_rounded, size: 15),
                            label: const FittedBox(
                              fit: BoxFit.scaleDown,
                              child: Text(
                                'WhatsApp',
                                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),

                    // Descripción expandible
                    AnimatedSize(
                      duration: const Duration(milliseconds: 240),
                      curve: Curves.easeOutCubic,
                      alignment: Alignment.topLeft,
                      child: _expanded && p.description.isNotEmpty
                          ? Padding(
                              padding: const EdgeInsets.only(top: 10),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Divider(
                                    height: 16,
                                    color: isDark ? Colors.white12 : AppColors.line,
                                  ),
                                  Text(
                                    p.description,
                                    maxLines: 3,
                                    overflow: TextOverflow.ellipsis,
                                    style: TextStyle(
                                      fontSize: 12.5,
                                      height: 1.4,
                                      color: isDark ? Colors.white70 : AppColors.ink,
                                    ),
                                  ),
                                  const SizedBox(height: 6),
                                  Text(
                                    'Ver ficha completa →',
                                    style: TextStyle(
                                      fontSize: 12,
                                      fontWeight: FontWeight.w700,
                                      color: isDark ? AppColors.navyLight : AppColors.navy,
                                    ),
                                  ),
                                ],
                              ),
                            )
                          : const SizedBox(width: double.infinity),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ExpandButton extends StatelessWidget {
  final bool expanded;
  final VoidCallback onTap;
  const _ExpandButton({required this.expanded, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return InkWell(
      borderRadius: BorderRadius.circular(20),
      onTap: onTap,
      child: Container(
        width: 26,
        height: 26,
        margin: const EdgeInsets.only(left: 6),
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF262246) : AppColors.neutralBg,
          shape: BoxShape.circle,
        ),
        child: AnimatedRotation(
          turns: expanded ? 0.125 : 0,
          duration: const Duration(milliseconds: 220),
          curve: Curves.easeOutCubic,
          child: Icon(
            Icons.add,
            size: 16,
            color: isDark ? AppColors.navyLight : AppColors.navy,
          ),
        ),
      ),
    );
  }
}

class _SpecChip extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool isDark;
  const _SpecChip({
    required this.icon,
    required this.label,
    required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF262246) : const Color(0xFFF1EFF7),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            size: 13.5,
            color: isDark ? AppColors.navyLight : AppColors.navy,
          ),
          const SizedBox(width: 4),
          Text(
            label,
            style: TextStyle(
              fontSize: 11.5,
              fontWeight: FontWeight.w600,
              color: isDark ? Colors.white70 : AppColors.ink,
            ),
          ),
        ],
      ),
    );
  }
}

/// Menú contextual moderno desplegado al mantener presionada una propiedad
class _PropertyQuickActionSheet extends StatelessWidget {
  final Property property;
  final OdooClient odoo;
  final NumberFormat currency;

  const _PropertyQuickActionSheet({
    required this.property,
    required this.odoo,
    required this.currency,
  });

  Future<void> _shareWhatsApp(BuildContext context) async {
    Navigator.of(context).pop();
    final title = property.title.isNotEmpty ? property.title : property.reference;
    final price = currency.format(property.displayPrice);
    final msg = Uri.encodeComponent(
      'Hola, te comparto esta propiedad de Inmobi:\n'
      '*$title*\n'
      'Precio: $price\n'
      'Ubicación: ${property.city} ${property.sector}\n'
      'Ver catálogo: https://inmobi.com.ec/catalogo/',
    );
    final url = Uri.parse('https://wa.me/?text=$msg');
    if (await canLaunchUrl(url)) {
      await launchUrl(url, mode: LaunchMode.externalApplication);
    }
  }

  void _copyLink(BuildContext context) {
    Navigator.of(context).pop();
    final link = 'https://inmobi.com.ec/catalogo/';
    Clipboard.setData(ClipboardData(text: link));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Enlace del catálogo copiado al portapapeles.'),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final p = property;

    return Container(
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF161330) : Colors.white,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      ),
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Asa superior
            Container(
              width: 38,
              height: 4,
              decoration: BoxDecoration(
                color: isDark ? Colors.white24 : Colors.black12,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(height: 16),

            // Encabezado de la propiedad
            Row(
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: SizedBox(
                    width: 52,
                    height: 52,
                    child: OdooImage(
                      odoo: odoo,
                      model: 'estate.property',
                      id: p.id,
                      field: 'image_main',
                      width: 140,
                      height: 140,
                    ),
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        p.title.isNotEmpty ? p.title : p.reference,
                        style: const TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w800,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 3),
                      Text(
                        '${p.city} ${p.sector} · ${currency.format(p.displayPrice)}',
                        style: const TextStyle(
                          fontSize: 12.5,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFFD81F26),
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Divider(color: isDark ? Colors.white12 : AppColors.line),
            const SizedBox(height: 6),

            // Acciones Rápidas
            _QuickActionTile(
              icon: Icons.picture_as_pdf_outlined,
              color: const Color(0xFFD81F26),
              title: 'Descargar / Compartir Ficha PDF',
              onTap: () {
                Navigator.of(context).pop();
                FichaDownloader.start(context: context, odoo: odoo, property: p);
              },
            ),
            _QuickActionTile(
              icon: Icons.chat_bubble_outline_rounded,
              color: const Color(0xFF25D366),
              title: 'Compartir por WhatsApp',
              onTap: () => _shareWhatsApp(context),
            ),
            _QuickActionTile(
              icon: Icons.calendar_month_outlined,
              color: const Color(0xFF28235D),
              title: 'Agendar Visita a esta Propiedad',
              onTap: () {
                Navigator.of(context).pop();
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => VisitFormScreen(
                      initialPropertyId: p.id,
                      initialPropertyName: p.title.isNotEmpty ? p.title : p.reference,
                    ),
                  ),
                );
              },
            ),
            _QuickActionTile(
              icon: Icons.link_rounded,
              color: const Color(0xFF0284C7),
              title: 'Copiar Enlace del Catálogo Web',
              onTap: () => _copyLink(context),
            ),
            _QuickActionTile(
              icon: Icons.edit_outlined,
              color: const Color(0xFF7C3AED),
              title: 'Editar Datos de la Propiedad',
              onTap: () {
                Navigator.of(context).pop();
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => PropertyFormScreen(existing: p),
                  ),
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _QuickActionTile extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String title;
  final VoidCallback onTap;

  const _QuickActionTile({
    required this.icon,
    required this.color,
    required this.title,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return ListTile(
      dense: true,
      contentPadding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
      leading: Container(
        width: 38,
        height: 38,
        decoration: BoxDecoration(
          color: color.withValues(alpha: isDark ? 0.18 : 0.1),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Icon(icon, color: color, size: 20),
      ),
      title: Text(
        title,
        style: const TextStyle(
          fontSize: 13.5,
          fontWeight: FontWeight.w600,
        ),
      ),
      trailing: const Icon(
        Icons.chevron_right_rounded,
        size: 18,
        color: AppColors.mutedLight,
      ),
      onTap: onTap,
    );
  }
}
