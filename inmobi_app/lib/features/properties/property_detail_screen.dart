import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../core/api/odoo_client.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/app_badge.dart';
import '../../core/widgets/odoo_image.dart';
import '../../core/widgets/states.dart';
import '../auth/auth_service.dart';
import '../contracts/contract_list_screen.dart';
import '../documents/document_service.dart';
import '../documents/documents_section.dart';
import 'property_form_screen.dart';
import 'property_gallery.dart';
import 'property_model.dart';
import 'property_service.dart';

class PropertyDetailScreen extends StatefulWidget {
  final int propertyId;
  const PropertyDetailScreen({super.key, required this.propertyId});

  @override
  State<PropertyDetailScreen> createState() => _PropertyDetailScreenState();
}

class _PropertyDetailScreenState extends State<PropertyDetailScreen> {
  late final OdooClient _odoo;
  Property? _property;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _odoo = context.read<AuthService>().odoo;
    _load();
  }

  Future<void> _load() async {
    try {
      final service = PropertyService(_odoo);
      final p = await service.detail(widget.propertyId);
      setState(() => _property = p);
    } catch (e) {
      setState(() => _error = 'No se pudo cargar la propiedad.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _openEdit() async {
    final saved = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => PropertyFormScreen(existing: _property),
      ),
    );
    if (saved == true) _load();
  }

  @override
  Widget build(BuildContext context) {
    final currency = NumberFormat.currency(
      locale: 'es_EC',
      symbol: '\$',
      decimalDigits: 0,
    );

    return Scaffold(
      appBar: AppBar(
        title: const Text('Propiedad'),
        actions: [
          if (_property != null)
            IconButton(
              icon: const Icon(Icons.edit_outlined),
              onPressed: _openEdit,
            ),
        ],
      ),
      body: _loading
          ? const LoadingView()
          : _error != null
          ? MessageView(
              icon: Icons.error_outline,
              message: _error!,
              onRetry: _load,
            )
          : _buildBody(currency),
    );
  }

  Widget _buildBody(NumberFormat currency) {
    final p = _property!;
    final dateFmt = DateFormat('d MMM yyyy', 'es_EC');

    return ListView(
      padding: EdgeInsets.zero,
      children: [
        Stack(
          children: [
            AspectRatio(
              aspectRatio: 16 / 10,
              child: Hero(
                tag: 'property-image-${p.id}',
                child: OdooImage(
                  odoo: _odoo,
                  model: 'estate.property',
                  id: p.id,
                  field: 'image_main',
                  width: 900,
                  height: 560,
                  errorBuilder: (_) => Container(
                    color: AppColors.navy.withValues(alpha: 0.08),
                    child: const Icon(
                      Icons.home_outlined,
                      size: 64,
                      color: AppColors.navy,
                    ),
                  ),
                ),
              ),
            ),
            Positioned(
              top: 14,
              right: 14,
              child: AppBadge(
                label: PropertyStateLabel.label(p.state),
                color: Colors.white,
                background: PropertyStateLabel.color(
                  p.state,
                ).withValues(alpha: 0.92),
              ),
            ),
            if (p.isExclusive)
              Positioned(
                top: 14,
                left: 14,
                child: AppBadge(
                  label: 'Exclusiva',
                  color: Colors.white,
                  background: AppColors.accent.withValues(alpha: 0.92),
                ),
              ),
          ],
        ),
        Padding(
          padding: const EdgeInsets.all(18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                p.title.isEmpty ? p.reference : p.title,
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 4),
              Row(
                children: [
                  const Icon(
                    Icons.place_outlined,
                    size: 15,
                    color: AppColors.muted,
                  ),
                  const SizedBox(width: 4),
                  Expanded(
                    child: Text(
                      [p.sector, p.city].where((s) => s.isNotEmpty).join(', '),
                      style: const TextStyle(color: AppColors.muted),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              Text(
                currency.format(p.displayPrice),
                style: const TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                  color: AppColors.navy,
                ),
              ),
              if (p.avmStatus.isNotEmpty) ...[
                const SizedBox(height: 6),
                Row(
                  children: [
                    AppBadge(
                      icon: Icons.insights_outlined,
                      label: 'AVM: ${PropertyAvmStyle.label(p.avmStatus)}',
                      color: PropertyAvmStyle.color(p.avmStatus),
                    ),
                    if (p.avmEstimatedPrice > 0) ...[
                      const SizedBox(width: 8),
                      Text(
                        'est. ${currency.format(p.avmEstimatedPrice)}',
                        style: const TextStyle(
                          fontSize: 11.5,
                          color: AppColors.mutedLight,
                        ),
                      ),
                    ],
                  ],
                ),
              ],
              const SizedBox(height: 16),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  _StatChip(
                    icon: Icons.square_foot,
                    label: '${p.area.toStringAsFixed(0)} m²',
                  ),
                  _StatChip(
                    icon: Icons.bed_outlined,
                    label: '${p.bedrooms} hab.',
                  ),
                  _StatChip(
                    icon: Icons.bathtub_outlined,
                    label: '${p.bathrooms.toStringAsFixed(0)} baños',
                  ),
                  if (p.parkingSpaces > 0)
                    _StatChip(
                      icon: Icons.directions_car_outlined,
                      label: '${p.parkingSpaces} parq.',
                    ),
                  if (p.floor > 0)
                    _StatChip(
                      icon: Icons.stairs_outlined,
                      label: 'Piso ${p.floor}',
                    ),
                  if (p.yearBuilt > 0)
                    _StatChip(
                      icon: Icons.calendar_month_outlined,
                      label: 'Año ${p.yearBuilt}',
                    ),
                ],
              ),
              const SizedBox(height: 18),
              OutlinedButton.icon(
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => ContractListScreen(
                      propertyId: p.id,
                      propertyTitle: p.title.isEmpty ? p.reference : p.title,
                    ),
                  ),
                ),
                icon: const Icon(Icons.description_outlined, size: 18),
                label: const Text('Ver contratos'),
              ),
              if (p.description.isNotEmpty) ...[
                const _SectionTitle('Descripción'),
                const SizedBox(height: 8),
                Text(
                  p.description,
                  style: const TextStyle(
                    fontSize: 13.5,
                    height: 1.5,
                    color: AppColors.ink,
                  ),
                ),
              ],
              const _SectionTitle('Ubicación'),
              const SizedBox(height: 8),
              _InfoCard(
                rows: [
                  if (p.street.isNotEmpty)
                    (
                      'Dirección',
                      p.streetNumber.isNotEmpty
                          ? '${p.street} ${p.streetNumber}'
                          : p.street,
                    ),
                  if (p.sector.isNotEmpty) ('Sector / Barrio', p.sector),
                  if (p.city.isNotEmpty) ('Ciudad', p.city),
                  if (p.zipCode.isNotEmpty) ('Código Postal', p.zipCode),
                  if (p.cadastralCode.isNotEmpty)
                    ('Clave Catastral', p.cadastralCode),
                ],
              ),
              const _SectionTitle('Personas relacionadas'),
              const SizedBox(height: 8),
              _InfoCard(
                rows: [
                  if (p.ownerName.isNotEmpty) ('Propietario', p.ownerName),
                  if (p.buyerName.isNotEmpty) ('Comprador', p.buyerName),
                  if (p.tenantName.isNotEmpty) ('Arrendatario', p.tenantName),
                  if (p.userName.isNotEmpty) ('Asesor responsable', p.userName),
                ],
              ),
              const _SectionTitle('Comercial'),
              const SizedBox(height: 8),
              _InfoCard(
                rows: [
                  ('Tipo de operación', p.isForSale ? 'Venta' : 'Arriendo'),
                  if (p.bottomPrice > 0)
                    ('Precio tope (mínimo)', currency.format(p.bottomPrice)),
                  ('Comisión', '${p.commissionPercentage.toStringAsFixed(1)}%'),
                  if (p.dateListed != null)
                    ('Publicada desde', dateFmt.format(p.dateListed!)),
                  if (p.daysOnMarket > 0)
                    ('Días en el mercado', '${p.daysOnMarket}'),
                ],
              ),
              const _SectionTitle('Galería'),
              const SizedBox(height: 8),
              PropertyGallerySection(odoo: _odoo, propertyId: p.id),
              const _SectionTitle('Documentos'),
              const SizedBox(height: 8),
              DocumentsSection(
                odoo: _odoo,
                owner: DocumentOwner.property(p.id),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _SectionTitle extends StatelessWidget {
  final String title;
  const _SectionTitle(this.title);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 22, bottom: 0),
      child: Text(
        title,
        style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
      ),
    );
  }
}

class _InfoCard extends StatelessWidget {
  final List<(String, String)> rows;
  const _InfoCard({required this.rows});

  @override
  Widget build(BuildContext context) {
    if (rows.isEmpty) {
      return const Text(
        'Sin información registrada.',
        style: TextStyle(color: AppColors.mutedLight, fontSize: 13),
      );
    }
    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
        child: Column(
          children: [
            for (int i = 0; i < rows.length; i++) ...[
              if (i > 0) const Divider(height: 1),
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 11),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        rows[i].$1,
                        style: const TextStyle(
                          fontSize: 12.5,
                          color: AppColors.mutedLight,
                        ),
                      ),
                    ),
                    Flexible(
                      child: Text(
                        rows[i].$2,
                        textAlign: TextAlign.end,
                        style: const TextStyle(
                          fontSize: 13.5,
                          fontWeight: FontWeight.w600,
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
    );
  }
}

class _StatChip extends StatelessWidget {
  final IconData icon;
  final String label;
  const _StatChip({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        border: Border.all(color: AppColors.line),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: AppColors.navy),
          const SizedBox(width: 5),
          Text(label, style: const TextStyle(fontSize: 12.5)),
        ],
      ),
    );
  }
}
