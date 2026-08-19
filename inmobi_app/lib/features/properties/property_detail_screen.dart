import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api/odoo_client.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/app_badge.dart';
import '../../core/widgets/expandable_section.dart';
import '../../core/widgets/odoo_image.dart';
import '../../core/widgets/states.dart';
import '../auth/auth_service.dart';
import '../contracts/contract_list_screen.dart';
import '../documents/document_service.dart';
import '../documents/documents_section.dart';
import '../finance/finance_screens.dart';
import '../offers/offer_screens.dart';
import '../visits/visit_form_screen.dart';
import 'price_history_section.dart';
import 'wordpress_section.dart';
import 'ficha_download.dart';
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
  String? _advisorPhone;
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
      if (p.userId != null) _loadAdvisorPhone(p.userId!);
    } catch (e) {
      setState(() => _error = 'No se pudo cargar la propiedad.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _loadAdvisorPhone(int userId) async {
    try {
      final rows = await _odoo.searchRead(
        model: 'res.users',
        domain: [
          ['id', '=', userId],
        ],
        fields: ['phone', 'mobile'],
        limit: 1,
      );
      if (rows.isEmpty) return;
      final phone = (rows.first['mobile'] ?? rows.first['phone'] ?? '')
          .toString();
      if (mounted && phone.isNotEmpty) setState(() => _advisorPhone = phone);
    } catch (_) {
      // Silencioso: si falla, la tarjeta del asesor simplemente no muestra botones de contacto.
    }
  }

  Future<void> _call(String phone) async {
    final uri = Uri(scheme: 'tel', path: phone);
    if (await canLaunchUrl(uri)) await launchUrl(uri);
  }

  Future<void> _whatsapp(String phone) async {
    final digits = phone.replaceAll(RegExp(r'[^0-9]'), '');
    final uri = Uri.parse('https://wa.me/$digits');
    if (await canLaunchUrl(uri))
      await launchUrl(uri, mode: LaunchMode.externalApplication);
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
              // Acciones rápidas, como en la barra de la ficha del ERP.
              Row(
                children: [
                  Expanded(
                    child: _QuickAction(
                      icon: Icons.picture_as_pdf_outlined,
                      label: 'Ficha PDF',
                      onTap: () => FichaDownloader.start(
                        context: context,
                        odoo: _odoo,
                        propertyId: p.id,
                        propertyTitle: p.title.isEmpty ? p.reference : p.title,
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _QuickAction(
                      icon: Icons.event_available_outlined,
                      label: 'Agendar',
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => VisitFormScreen(
                            initialPropertyId: p.id,
                            initialPropertyName: p.title.isEmpty
                                ? p.reference
                                : p.title,
                          ),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _QuickAction(
                      icon: Icons.handshake_outlined,
                      label: 'Ofertas',
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => OfferListScreen(
                            propertyId: p.id,
                            propertyName: p.title.isEmpty
                                ? p.reference
                                : p.title,
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: _QuickAction(
                      icon: Icons.description_outlined,
                      label: 'Contratos',
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => ContractListScreen(
                            propertyId: p.id,
                            propertyTitle: p.title.isEmpty
                                ? p.reference
                                : p.title,
                          ),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _QuickAction(
                      icon: Icons.request_quote_outlined,
                      label: 'Gastos',
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => ExpenseListScreen(
                            propertyId: p.id,
                            propertyName: p.title.isEmpty
                                ? p.reference
                                : p.title,
                          ),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _QuickAction(
                      icon: Icons.assessment_outlined,
                      label: 'Tasaciones',
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => AppraisalListScreen(propertyId: p.id),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
              if (p.userName.isNotEmpty) ...[
                const SizedBox(height: 18),
                _AdvisorCard(
                  name: p.userName,
                  phone: _advisorPhone,
                  onCall: _call,
                  onWhatsapp: _whatsapp,
                ),
              ],
              const SizedBox(height: 18),
              ExpandableSection(
                title: 'Ubicación',
                child: _InfoCard(
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
              ),
              const SizedBox(height: 8),
              ExpandableSection(
                title: 'Personas relacionadas',
                child: _InfoCard(
                  rows: [
                    if (p.ownerName.isNotEmpty) ('Propietario', p.ownerName),
                    if (p.buyerName.isNotEmpty) ('Comprador', p.buyerName),
                    if (p.tenantName.isNotEmpty) ('Arrendatario', p.tenantName),
                  ],
                ),
              ),
              const SizedBox(height: 8),
              ExpandableSection(
                title: 'Comercial',
                child: _InfoCard(
                  rows: [
                    ('Tipo de operación', p.isForSale ? 'Venta' : 'Arriendo'),
                    if (p.bottomPrice > 0)
                      ('Precio tope (mínimo)', currency.format(p.bottomPrice)),
                    (
                      'Comisión',
                      '${p.commissionPercentage.toStringAsFixed(1)}%',
                    ),
                    if (p.dateListed != null)
                      ('Publicada desde', dateFmt.format(p.dateListed!)),
                    if (p.daysOnMarket > 0)
                      ('Días en el mercado', '${p.daysOnMarket}'),
                  ],
                ),
              ),
              if (p.description.isNotEmpty) ...[
                const SizedBox(height: 8),
                ExpandableSection(
                  title: 'Descripción',
                  child: Text(
                    p.description,
                    style: const TextStyle(
                      fontSize: 13.5,
                      height: 1.5,
                      color: AppColors.ink,
                    ),
                  ),
                ),
              ],
              const SizedBox(height: 8),
              ExpandableSection(
                title: 'Historial de precios',
                child: PriceHistorySection(odoo: _odoo, propertyId: p.id),
              ),
              const SizedBox(height: 8),
              ExpandableSection(
                title: 'Sitio web',
                initiallyExpanded: true,
                child: WordpressSection(
                  odoo: _odoo,
                  property: p,
                  onChanged: _load,
                ),
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

/// Botón cuadrado de acción rápida (Ficha PDF, Agendar, Contratos).
class _QuickAction extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  const _QuickAction({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 6),
        decoration: BoxDecoration(
          color: AppColors.neutralBg,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          children: [
            Icon(icon, size: 21, color: AppColors.navy),
            const SizedBox(height: 6),
            Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                fontSize: 11.5,
                fontWeight: FontWeight.w600,
                color: AppColors.navy,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AdvisorCard extends StatelessWidget {
  final String name;
  final String? phone;
  final ValueChanged<String> onCall;
  final ValueChanged<String> onWhatsapp;

  const _AdvisorCard({
    required this.name,
    required this.phone,
    required this.onCall,
    required this.onWhatsapp,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.neutralBg,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          InitialsAvatar(text: name, size: 44),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Asesor responsable',
                  style: TextStyle(fontSize: 11, color: AppColors.mutedLight),
                ),
                const SizedBox(height: 2),
                Text(
                  name,
                  style: const TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 14,
                  ),
                ),
              ],
            ),
          ),
          if (phone != null) ...[
            _ContactIconButton(
              icon: Icons.call,
              background: AppColors.navy,
              onTap: () => onCall(phone!),
            ),
            const SizedBox(width: 8),
            _ContactIconButton(
              icon: Icons.chat,
              background: const Color(0xFF25D366),
              onTap: () => onWhatsapp(phone!),
            ),
          ],
        ],
      ),
    );
  }
}

class _ContactIconButton extends StatelessWidget {
  final IconData icon;
  final Color background;
  final VoidCallback onTap;
  const _ContactIconButton({
    required this.icon,
    required this.background,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(20),
      onTap: onTap,
      child: Container(
        width: 38,
        height: 38,
        decoration: BoxDecoration(color: background, shape: BoxShape.circle),
        child: Icon(icon, color: Colors.white, size: 18),
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
