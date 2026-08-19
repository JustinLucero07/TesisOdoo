import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/api/odoo_client.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/app_badge.dart';
import '../../core/widgets/odoo_image.dart';
import 'property_detail_screen.dart';
import 'property_model.dart';

/// Tarjeta de propiedad "de imagen grande" (foto arriba, info abajo) en vez
/// de la miniatura apretada al costado — dan más aire y se ven mejor los
/// detalles. Un botón "+" permite ver un resumen de la descripción sin salir
/// de la lista; tocar el resto de la tarjeta abre la ficha completa.
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

  @override
  Widget build(BuildContext context) {
    final p = widget.property;
    final photoCount = p.imageIds.isEmpty ? 1 : p.imageIds.length;
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) => PropertyDetailScreen(propertyId: p.id),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Stack(
              children: [
                AspectRatio(
                  aspectRatio: 16 / 10,
                  child: Hero(
                    tag: 'property-image-${p.id}',
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
                                Icons.home_outlined,
                                size: 40,
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
                                  Icons.home_outlined,
                                  size: 40,
                                  color: AppColors.navy,
                                ),
                              ),
                            ),
                          ),
                  ),
                ),
                if (photoCount > 1) ...[
                  Positioned(
                    bottom: 10,
                    left: 0,
                    right: 0,
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: List.generate(
                        photoCount,
                        (i) => AnimatedContainer(
                          duration: const Duration(milliseconds: 200),
                          margin: const EdgeInsets.symmetric(horizontal: 2),
                          width: i == _photoIndex ? 14 : 5,
                          height: 5,
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(
                              alpha: i == _photoIndex ? 0.95 : 0.55,
                            ),
                            borderRadius: BorderRadius.circular(3),
                          ),
                        ),
                      ),
                    ),
                  ),
                  Positioned(
                    bottom: 10,
                    left: 10,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 7,
                        vertical: 3,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.black.withValues(alpha: 0.55),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text(
                        '${_photoIndex + 1}/$photoCount',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 10.5,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ),
                ],
                if (p.isExclusive)
                  Positioned(
                    top: 10,
                    left: 10,
                    child: AppBadge(
                      label: 'Exclusiva',
                      color: Colors.white,
                      background: AppColors.accent.withValues(alpha: 0.92),
                    ),
                  ),
                Positioned(
                  top: 10,
                  right: 10,
                  child: AppBadge(
                    label: PropertyStateLabel.label(p.state),
                    color: Colors.white,
                    background: PropertyStateLabel.color(
                      p.state,
                    ).withValues(alpha: 0.92),
                  ),
                ),
              ],
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 12, 10, 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Text(
                          p.title.isEmpty ? p.reference : p.title,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            fontWeight: FontWeight.w700,
                            fontSize: 15,
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
                  const SizedBox(height: 3),
                  Row(
                    children: [
                      const Icon(
                        Icons.place_outlined,
                        size: 13,
                        color: AppColors.mutedLight,
                      ),
                      const SizedBox(width: 3),
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
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 12,
                    children: [
                      _MiniStat(
                        icon: Icons.square_foot,
                        label: '${p.area.toStringAsFixed(0)} m²',
                      ),
                      _MiniStat(
                        icon: Icons.bed_outlined,
                        label: '${p.bedrooms}',
                      ),
                      _MiniStat(
                        icon: Icons.bathtub_outlined,
                        label: p.bathrooms.toStringAsFixed(0),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    widget.currency.format(p.displayPrice),
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      color: AppColors.navy,
                      fontSize: 16,
                    ),
                  ),
                  AnimatedSize(
                    duration: const Duration(milliseconds: 260),
                    curve: Curves.easeOutCubic,
                    alignment: Alignment.topLeft,
                    child: _expanded && p.description.isNotEmpty
                        ? Padding(
                            padding: const EdgeInsets.only(top: 10),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  p.description,
                                  maxLines: 3,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                    fontSize: 12.5,
                                    height: 1.4,
                                    color: AppColors.ink,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  'Ver ficha completa →',
                                  style: TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.w600,
                                    color: AppColors.navy.withValues(
                                      alpha: 0.85,
                                    ),
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
    );
  }
}

class _ExpandButton extends StatelessWidget {
  final bool expanded;
  final VoidCallback onTap;
  const _ExpandButton({required this.expanded, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(20),
      onTap: onTap,
      child: Container(
        width: 28,
        height: 28,
        margin: const EdgeInsets.only(left: 6),
        decoration: BoxDecoration(
          color: AppColors.neutralBg,
          shape: BoxShape.circle,
        ),
        child: AnimatedRotation(
          turns: expanded ? 0.125 : 0,
          duration: const Duration(milliseconds: 220),
          curve: Curves.easeOutCubic,
          child: const Icon(Icons.add, size: 17, color: AppColors.navy),
        ),
      ),
    );
  }
}

class _MiniStat extends StatelessWidget {
  final IconData icon;
  final String label;
  const _MiniStat({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14, color: AppColors.mutedLight),
        const SizedBox(width: 3),
        Text(
          label,
          style: const TextStyle(fontSize: 12, color: AppColors.muted),
        ),
      ],
    );
  }
}
