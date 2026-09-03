import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api/odoo_client.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/phone_utils.dart';
import '../../core/widgets/app_badge.dart';
import '../../core/widgets/expandable_section.dart';
import '../../core/widgets/odoo_image.dart';
import '../../core/widgets/states.dart';
import '../auth/auth_service.dart';
import '../contacts/contact_detail_screen.dart';
import '../contracts/contract_list_screen.dart';
import '../crm/lead_form_screen.dart';
import '../documents/document_service.dart';
import '../documents/documents_section.dart';
import '../finance/finance_screens.dart';
import '../offers/offer_screens.dart';
import '../visits/visit_form_screen.dart';
import 'ficha_download.dart';
import 'price_history_section.dart';
import 'property_form_screen.dart';
import 'property_gallery.dart';
import 'property_model.dart';
import 'property_service.dart';
import 'wordpress_section.dart';

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
  // Teléfono de cada persona relacionada, por id de contacto — un mismo
  // contacto puede ser propietario y comprador a la vez, así que se
  // guarda por id en vez de un campo por rol.
  final Map<int, String> _relatedPhones = {};
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
      _loadRelatedPhones(p);
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
      // Silencioso
    }
  }

  /// Trae el teléfono de propietario/comprador/arrendatario en una sola
  /// consulta a res.partner — mismo patrón que _loadAdvisorPhone, pero
  /// agrupado porque los tres son el mismo modelo.
  Future<void> _loadRelatedPhones(Property p) async {
    final ids = {
      if (p.ownerId != null) p.ownerId!,
      if (p.buyerId != null) p.buyerId!,
      if (p.tenantId != null) p.tenantId!,
    };
    if (ids.isEmpty) return;
    try {
      final rows = await _odoo.searchRead(
        model: 'res.partner',
        domain: [
          ['id', 'in', ids.toList()],
        ],
        fields: ['id', 'phone', 'mobile'],
      );
      if (!mounted) return;
      setState(() {
        for (final row in rows) {
          final phone = (row['mobile'] ?? row['phone'] ?? '').toString();
          if (phone.isNotEmpty) _relatedPhones[row['id'] as int] = phone;
        }
      });
    } catch (_) {
      // Silencioso: si no hay teléfono simplemente no se muestran los botones.
    }
  }

  Future<void> _call(String phone) => PhoneUtils.call(phone);

  Future<void> _whatsappAdvisor(String phone) async {
    final p = _property;
    final title = p != null ? (p.title.isEmpty ? p.reference : p.title) : '';
    await PhoneUtils.whatsapp(
      phone,
      text: 'Hola, te contacto sobre la propiedad $title (Ref: ${p?.reference ?? ''}).',
    );
  }

  /// WhatsApp genérico para propietario/comprador/arrendatario — mismo
  /// mensaje que el del asesor, sin repetir la lógica de armar el link.
  Future<void> _whatsappRelated(String phone) => _whatsappAdvisor(phone);

  /// Abre WhatsApp con mensaje comercial para comprar/consultar
  Future<void> _openBuyWhatsapp() async {
    if (_property == null) return;
    await FichaDownloader.shareCommercialWhatsapp(
      property: _property!,
      phone: _advisorPhone,
    );
  }

  /// Abre ubicación en Google Maps
  bool get _hasGpsCoords {
    final p = _property;
    if (p == null) return false;
    return p.latitude != 0.0 && p.longitude != 0.0;
  }

  String _buildLocationQuery() {
    final p = _property;
    if (p == null) return 'Ecuador';
    final parts = [
      if (p.street.isNotEmpty) p.street,
      if (p.streetNumber.isNotEmpty) p.streetNumber,
      if (p.sector.isNotEmpty) p.sector,
      if (p.city.isNotEmpty) p.city,
      'Ecuador',
    ];
    if (parts.length <= 1) {
      return [p.title, p.city, 'Ecuador'].where((s) => s.isNotEmpty).join(', ');
    }
    return parts.join(', ');
  }

  /// Abre la ubicación en Google Maps priorizando coordenadas GPS de Odoo
  Future<void> _openInGoogleMaps() async {
    final p = _property;
    if (p == null) return;
    final String url;
    if (_hasGpsCoords) {
      url = 'https://www.google.com/maps/search/?api=1&query=${p.latitude},${p.longitude}';
    } else {
      final query = _buildLocationQuery();
      url = 'https://www.google.com/maps/search/?api=1&query=${Uri.encodeComponent(query)}';
    }

    try {
      final uri = Uri.parse(url);
      final launched = await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (!launched) {
        await launchUrl(uri, mode: LaunchMode.platformDefault);
      }
    } catch (_) {
      try {
        await launchUrl(Uri.parse(url), mode: LaunchMode.platformDefault);
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('No se pudo abrir Google Maps.')),
          );
        }
      }
    }
  }

  /// Abre la ubicación en Apple Maps (Maps de iOS) priorizando coordenadas GPS de Odoo
  Future<void> _openInAppleMaps() async {
    final p = _property;
    if (p == null) return;
    final String url;
    final title = p.title.isNotEmpty ? p.title : p.reference;
    if (_hasGpsCoords) {
      url = 'https://maps.apple.com/?ll=${p.latitude},${p.longitude}&q=${Uri.encodeComponent(title)}';
    } else {
      final query = _buildLocationQuery();
      url = 'https://maps.apple.com/?q=${Uri.encodeComponent(query)}';
    }

    try {
      final uri = Uri.parse(url);
      final launched = await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (!launched) {
        await launchUrl(uri, mode: LaunchMode.platformDefault);
      }
    } catch (_) {
      try {
        await launchUrl(Uri.parse(url), mode: LaunchMode.platformDefault);
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('No se pudo abrir Apple Maps.')),
          );
        }
      }
    }
  }

  /// Abre ruta en Waze GPS priorizando coordenadas GPS de Odoo
  Future<void> _openInWaze() async {
    final p = _property;
    if (p == null) return;
    final String url;
    if (_hasGpsCoords) {
      url = 'https://waze.com/ul?ll=${p.latitude},${p.longitude}&navigate=yes';
    } else {
      final query = _buildLocationQuery();
      url = 'https://waze.com/ul?q=${Uri.encodeComponent(query)}&navigate=yes';
    }

    try {
      final uri = Uri.parse(url);
      final launched = await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (!launched) {
        await launchUrl(uri, mode: LaunchMode.platformDefault);
      }
    } catch (_) {
      try {
        await launchUrl(Uri.parse(url), mode: LaunchMode.platformDefault);
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('No se pudo abrir Waze.')),
          );
        }
      }
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
          if (_property != null) ...[
            IconButton(
              icon: const Icon(Icons.calendar_month_outlined),
              tooltip: 'Agendar Visita',
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => VisitFormScreen(
                    initialPropertyId: _property!.id,
                    initialPropertyName: _property!.title,
                  ),
                ),
              ),
            ),
            PopupMenuButton<String>(
              icon: const Icon(Icons.more_vert_rounded),
              tooltip: 'Opciones de documento',
              onSelected: (val) {
                if (val == 'captacion') {
                  FichaDownloader.openCaptureSheet(
                    context: context,
                    odoo: _odoo,
                    property: _property!,
                  );
                } else if (val == 'ficha') {
                  FichaDownloader.start(
                    context: context,
                    odoo: _odoo,
                    property: _property!,
                  );
                } else if (val == 'edit') {
                  _openEdit();
                }
              },
              itemBuilder: (_) => [
                const PopupMenuItem(
                  value: 'captacion',
                  child: Row(
                    children: [
                      Icon(Icons.assignment_outlined, size: 18, color: Color(0xFFD81F26)),
                      SizedBox(width: 10),
                      Text('Hoja de Captación (PDF)'),
                    ],
                  ),
                ),
                const PopupMenuItem(
                  value: 'ficha',
                  child: Row(
                    children: [
                      Icon(Icons.picture_as_pdf_outlined, size: 18, color: Color(0xFF28235D)),
                      SizedBox(width: 10),
                      Text('Ficha Comercial (PDF)'),
                    ],
                  ),
                ),
                const PopupMenuDivider(),
                const PopupMenuItem(
                  value: 'edit',
                  child: Row(
                    children: [
                      Icon(Icons.edit_outlined, size: 18),
                      SizedBox(width: 10),
                      Text('Editar Propiedad'),
                    ],
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
      bottomNavigationBar: _property != null ? _buildBottomStickyBar() : null,
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

  /// Barra inferior fija para acceso instantáneo a WhatsApp y Ficha PDF
  Widget _buildBottomStickyBar() {
    final p = _property!;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colors = AppColors.of(context);
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 10, 16, 16),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1C1938) : Colors.white,
        border: Border(
          top: BorderSide(
            color: isDark ? Colors.white12 : colors.line,
          ),
        ),
        boxShadow: softShadow(opacity: isDark ? 0.25 : 0.08, isDark: isDark),
      ),
      child: SafeArea(
        top: false,
        child: Row(
          children: [
            // Botón Compartir Ficha
            OutlinedButton.icon(
              onPressed: () => FichaDownloader.start(
                context: context,
                odoo: _odoo,
                property: p,
              ),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
                side: BorderSide(
                  color: isDark ? Colors.white24 : colors.line,
                ),
              ),
              icon: const Icon(Icons.share_rounded, size: 17),
              label: const Text('Ficha PDF', style: TextStyle(fontWeight: FontWeight.w700)),
            ),
            const SizedBox(width: 10),

            // Botón WhatsApp Comprar / Consultar
            Expanded(
              child: ElevatedButton.icon(
                onPressed: _openBuyWhatsapp,
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF25D366),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 13),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                  ),
                ),
                icon: const Icon(Icons.chat_bubble_rounded, size: 18),
                label: Text(
                  p.isForSale ? 'Comprar por WhatsApp' : 'Arrendar por WhatsApp',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 13.5,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBody(NumberFormat currency) {
    final p = _property!;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colors = AppColors.of(context);
    final dateFmt = DateFormat('d MMM yyyy', 'es_EC');
    final pricePerM2 = (p.area > 0 && p.displayPrice > 0)
        ? (p.displayPrice / p.area)
        : null;

    return ListView(
      padding: const EdgeInsets.only(bottom: 36),
      children: [
        // Foto de portada con badge interactiva y zoom
        Stack(
          children: [
            GestureDetector(
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => PropertyFullscreenViewer(
                    odoo: _odoo,
                    images: [
                      (model: 'estate.property', id: p.id, field: 'image_main'),
                    ],
                  ),
                  fullscreenDialog: true,
                ),
              ),
              child: AspectRatio(
                aspectRatio: 16 / 10,
                child: OdooImage(
                  odoo: _odoo,
                  model: 'estate.property',
                  id: p.id,
                  field: 'image_main',
                  width: 900,
                  height: 560,
                  errorBuilder: (_) => Container(
                    color: colors.navy.withValues(alpha: 0.08),
                    child: Icon(
                      Icons.home_outlined,
                      size: 64,
                      color: colors.navy,
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
                  colors,
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
                  background: colors.accent.withValues(alpha: 0.92),
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
                  fontSize: 21,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 4),
              Row(
                children: [
                  Icon(
                    Icons.location_on_outlined,
                    size: 15,
                    color: colors.muted,
                  ),
                  const SizedBox(width: 4),
                  Expanded(
                    child: Text(
                      [p.sector, p.city].where((s) => s.isNotEmpty).join(', '),
                      style: TextStyle(color: colors.muted),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              Row(
                crossAxisAlignment: CrossAxisAlignment.baseline,
                textBaseline: TextBaseline.alphabetic,
                children: [
                  Text(
                    currency.format(p.displayPrice),
                    style: TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.w800,
                      color: isDark ? colors.navyLight : colors.navy,
                      letterSpacing: -0.6,
                    ),
                  ),
                  if (pricePerM2 != null) ...[
                    const SizedBox(width: 10),
                    Text(
                      '•  ${currency.format(pricePerM2)}/m²',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: colors.mutedLight,
                      ),
                    ),
                  ],
                ],
              ),
              if (p.avmStatus.isNotEmpty) ...[
                const SizedBox(height: 6),
                Row(
                  children: [
                    AppBadge(
                      icon: Icons.insights_outlined,
                      label: 'AVM: ${PropertyAvmStyle.label(p.avmStatus)}',
                      color: PropertyAvmStyle.color(p.avmStatus, colors),
                    ),
                    if (p.avmEstimatedPrice > 0) ...[
                      const SizedBox(width: 8),
                      Text(
                        'est. ${currency.format(p.avmEstimatedPrice)}',
                        style: TextStyle(
                          fontSize: 11.5,
                          color: colors.mutedLight,
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

              // Fila 1 de Acciones Rápidas
              Row(
                children: [
                  Expanded(
                    child: _QuickAction(
                      icon: Icons.picture_as_pdf_outlined,
                      label: 'Ficha PDF',
                      onTap: () => FichaDownloader.start(
                        context: context,
                        odoo: _odoo,
                        property: p,
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
                      icon: Icons.person_add_alt_1_outlined,
                      label: 'Nuevo Lead',
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => LeadFormScreen(
                            initialPropertyId: p.id,
                            initialPropertyName: p.title.isEmpty
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

              // Fila 2 de Acciones Rápidas
              Row(
                children: [
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
                  const SizedBox(width: 10),
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
                ],
              ),
              const SizedBox(height: 10),

              // Fila 3: Documento de Captación
              Row(
                children: [
                  Expanded(
                    child: _QuickAction(
                      icon: Icons.assignment_outlined,
                      label: 'Hoja de Captación (PDF)',
                      onTap: () => FichaDownloader.openCaptureSheet(
                        context: context,
                        odoo: _odoo,
                        property: p,
                      ),
                    ),
                  ),
                ],
              ),

              if (p.userName.isNotEmpty) ...[
                const SizedBox(height: 18),
                _AdvisorCard(
                  label: 'Asesor responsable',
                  name: p.userName,
                  phone: _advisorPhone,
                  onCall: _call,
                  onWhatsapp: _whatsappAdvisor,
                ),
              ],
              const SizedBox(height: 18),

              // Sección Ubicación con botones de Navegación GPS directa
              ExpandableSection(
                title: 'Ubicación y Navegación GPS',
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
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
                        if (p.latitude != 0.0 && p.longitude != 0.0)
                          (
                            'Coordenadas GPS',
                            '${p.latitude.toStringAsFixed(6)}, ${p.longitude.toStringAsFixed(6)}',
                          ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: _openInGoogleMaps,
                            style: OutlinedButton.styleFrom(
                              padding: const EdgeInsets.symmetric(vertical: 10),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                            ),
                            icon: const Icon(Icons.location_on_outlined, size: 18, color: Color(0xFFEA4335)),
                            label: const Text('Google Maps', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: _openInAppleMaps,
                            style: OutlinedButton.styleFrom(
                              padding: const EdgeInsets.symmetric(vertical: 10),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                            ),
                            icon: const Icon(Icons.map_outlined, size: 18, color: Color(0xFF28235D)),
                            label: const Text('Apple Maps', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: _openInWaze,
                            style: OutlinedButton.styleFrom(
                              padding: const EdgeInsets.symmetric(vertical: 10),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                            ),
                            icon: const Icon(Icons.navigation_rounded, size: 18, color: Color(0xFF33CCFF)),
                            label: const Text('Waze GPS', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 8),

              ExpandableSection(
                title: 'Personas relacionadas',
                child: _PeopleInfoCard(
                  rows: [
                    if (p.ownerName.isNotEmpty)
                      (
                        label: 'Propietario',
                        name: p.ownerName,
                        contactId: p.ownerId,
                        phone: p.ownerId != null ? _relatedPhones[p.ownerId] : null,
                      ),
                    if (p.buyerName.isNotEmpty)
                      (
                        label: 'Comprador',
                        name: p.buyerName,
                        contactId: p.buyerId,
                        phone: p.buyerId != null ? _relatedPhones[p.buyerId] : null,
                      ),
                    if (p.tenantName.isNotEmpty)
                      (
                        label: 'Arrendatario',
                        name: p.tenantName,
                        contactId: p.tenantId,
                        phone: p.tenantId != null ? _relatedPhones[p.tenantId] : null,
                      ),
                  ],
                  onCall: _call,
                  onWhatsapp: _whatsappRelated,
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
                    style: TextStyle(
                      fontSize: 13.5,
                      height: 1.5,
                      color: colors.ink,
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

              const SizedBox(height: 18),
              _CaptureSheetSection(
                odoo: _odoo,
                property: p,
                onChanged: _load,
              ),

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

/// Fila de una persona relacionada (propietario/comprador/arrendatario):
/// misma tarjeta compacta que _InfoCard, pero el nombre lleva a la ficha
/// completa del contacto y trae los accesos directos de llamar/WhatsApp
/// cuando hay teléfono cargado.
class _PeopleInfoCard extends StatelessWidget {
  final List<({String label, String name, int? contactId, String? phone})> rows;
  final ValueChanged<String> onCall;
  final ValueChanged<String> onWhatsapp;

  const _PeopleInfoCard({
    required this.rows,
    required this.onCall,
    required this.onWhatsapp,
  });

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.of(context);
    if (rows.isEmpty) {
      return Text(
        'Sin información registrada.',
        style: TextStyle(color: colors.mutedLight, fontSize: 13),
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
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        rows[i].label,
                        style: TextStyle(
                          fontSize: 12.5,
                          color: colors.mutedLight,
                        ),
                      ),
                    ),
                    Flexible(
                      child: InkWell(
                        borderRadius: BorderRadius.circular(6),
                        onTap: rows[i].contactId == null
                            ? null
                            : () => Navigator.of(context).push(
                                  MaterialPageRoute(
                                    builder: (_) => ContactDetailScreen(
                                      contactId: rows[i].contactId!,
                                    ),
                                  ),
                                ),
                        child: Text(
                          rows[i].name,
                          textAlign: TextAlign.end,
                          style: TextStyle(
                            fontSize: 13.5,
                            fontWeight: FontWeight.w600,
                            color: rows[i].contactId != null
                                ? colors.navy
                                : null,
                            decoration: rows[i].contactId != null
                                ? TextDecoration.underline
                                : null,
                            decorationColor: colors.navy.withValues(alpha: 0.35),
                          ),
                        ),
                      ),
                    ),
                    if (rows[i].phone != null) ...[
                      const SizedBox(width: 6),
                      _SmallContactIcon(
                        icon: Icons.call,
                        color: colors.navy,
                        onTap: () => onCall(rows[i].phone!),
                      ),
                      const SizedBox(width: 2),
                      _SmallContactIcon(
                        icon: Icons.chat,
                        color: const Color(0xFF25D366),
                        onTap: () => onWhatsapp(rows[i].phone!),
                      ),
                    ],
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

/// Ícono chico de llamar/WhatsApp para filas compactas — versión reducida
/// de _ContactIconButton, pensada para caber al lado de un nombre en vez
/// de en una tarjeta grande con avatar.
class _SmallContactIcon extends StatelessWidget {
  final IconData icon;
  final Color color;
  final VoidCallback onTap;
  const _SmallContactIcon({
    required this.icon,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(16),
      onTap: onTap,
      child: Container(
        width: 30,
        height: 30,
        alignment: Alignment.center,
        decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        child: Icon(icon, color: Colors.white, size: 14),
      ),
    );
  }
}

class _InfoCard extends StatelessWidget {
  final List<(String, String)> rows;
  const _InfoCard({required this.rows});

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.of(context);
    if (rows.isEmpty) {
      return Text(
        'Sin información registrada.',
        style: TextStyle(color: colors.mutedLight, fontSize: 13),
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
                        style: TextStyle(
                          fontSize: 12.5,
                          color: colors.mutedLight,
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

/// Botón cuadrado de acción rápida
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
    final colors = AppColors.of(context);
    return InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 6),
        decoration: BoxDecoration(
          color: colors.neutralBg,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          children: [
            Icon(icon, size: 21, color: colors.navy),
            const SizedBox(height: 6),
            Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 11.5,
                fontWeight: FontWeight.w600,
                color: colors.navy,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AdvisorCard extends StatelessWidget {
  final String label;
  final String name;
  final String? phone;
  final ValueChanged<String> onCall;
  final ValueChanged<String> onWhatsapp;

  const _AdvisorCard({
    required this.label,
    required this.name,
    required this.phone,
    required this.onCall,
    required this.onWhatsapp,
  });

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.of(context);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: colors.neutralBg,
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
                Text(
                  label,
                  style: TextStyle(fontSize: 11, color: colors.mutedLight),
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
              background: colors.navy,
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
    final colors = AppColors.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        border: Border.all(color: colors.line),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: colors.navy),
          const SizedBox(width: 5),
          Text(label, style: const TextStyle(fontSize: 12.5)),
        ],
      ),
    );
  }
}

/// Sección de Hoja de Captación con soporte para archivo subido (PDF/escaneado) y generación de plantilla
class _CaptureSheetSection extends StatelessWidget {
  final OdooClient odoo;
  final Property property;
  final VoidCallback onChanged;

  const _CaptureSheetSection({
    required this.odoo,
    required this.property,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colors = AppColors.of(context);
    final hasFile = property.hasCaptureSheet || property.captureSheetFilename.isNotEmpty;
    final fileName = property.captureSheetFilename.isNotEmpty
        ? property.captureSheetFilename
        : 'Hoja_Captacion_${property.id}.pdf';

    return Container(
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1E1A3E) : Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: isDark ? Colors.white12 : const Color(0xFFE2E8F0),
        ),
        boxShadow: softShadow(opacity: isDark ? 0.2 : 0.05, isDark: isDark),
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: const Color(0xFFD81F26).withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(
                  Icons.assignment_outlined,
                  size: 20,
                  color: Color(0xFFD81F26),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Hoja de Captación',
                      style: TextStyle(
                        fontWeight: FontWeight.w800,
                        fontSize: 14.5,
                      ),
                    ),
                    Text(
                      'Documento escaneado o PDF subido en Odoo',
                      style: TextStyle(
                        fontSize: 11,
                        color: colors.muted,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          if (hasFile) ...[
            Container(
              decoration: BoxDecoration(
                color: isDark
                    ? const Color(0xFF28235D).withValues(alpha: 0.5)
                    : const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: isDark ? Colors.white24 : const Color(0xFFCBD5E1),
                ),
              ),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              child: Row(
                children: [
                  const Icon(
                    Icons.picture_as_pdf_rounded,
                    color: Color(0xFFD81F26),
                    size: 26,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      fileName,
                      style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  IconButton(
                    visualDensity: VisualDensity.compact,
                    tooltip: 'Cambiar archivo',
                    icon: const Icon(
                      Icons.edit_outlined,
                      size: 20,
                      color: Color(0xFF28235D),
                    ),
                    onPressed: () async {
                      final ok = await FichaDownloader.uploadCaptureSheet(
                        context: context,
                        odoo: odoo,
                        propertyId: property.id,
                      );
                      if (ok) onChanged();
                    },
                  ),
                  IconButton(
                    visualDensity: VisualDensity.compact,
                    tooltip: 'Eliminar',
                    icon: const Icon(
                      Icons.delete_outline_rounded,
                      size: 20,
                      color: Color(0xFFD81F26),
                    ),
                    onPressed: () async {
                      final ok = await FichaDownloader.deleteCaptureSheet(
                        context: context,
                        odoo: odoo,
                        propertyId: property.id,
                      );
                      if (ok) onChanged();
                    },
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              height: 42,
              child: ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF28235D),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                onPressed: () => FichaDownloader.openCaptureSheet(
                  context: context,
                  odoo: odoo,
                  property: property,
                ),
                icon: const Icon(Icons.visibility_rounded, size: 18, color: Colors.white),
                label: const Text(
                  'Ver Hoja de Captación',
                  style: TextStyle(
                    fontSize: 13.5,
                    fontWeight: FontWeight.w700,
                    color: Colors.white,
                  ),
                ),
              ),
            ),
          ] else ...[
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              decoration: BoxDecoration(
                color: isDark
                    ? const Color(0xFF28235D).withValues(alpha: 0.2)
                    : colors.neutralBg,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: isDark ? Colors.white12 : colors.line,
                ),
              ),
              child: Row(
                children: [
                  Icon(Icons.info_outline_rounded, size: 18, color: colors.muted),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'No hay archivo de captación adjunto en esta propiedad.',
                      style: TextStyle(fontSize: 12, color: colors.muted),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => FichaDownloader.openCaptureSheet(
                      context: context,
                      odoo: odoo,
                      property: property,
                    ),
                    style: OutlinedButton.styleFrom(
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      padding: const EdgeInsets.symmetric(vertical: 10),
                    ),
                    icon: const Icon(Icons.picture_as_pdf_outlined, size: 16),
                    label: const Text(
                      'Generar PDF',
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () async {
                      final ok = await FichaDownloader.uploadCaptureSheet(
                        context: context,
                        odoo: odoo,
                        propertyId: property.id,
                      );
                      if (ok) onChanged();
                    },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFFD81F26),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      padding: const EdgeInsets.symmetric(vertical: 10),
                    ),
                    icon: const Icon(Icons.upload_file_rounded, size: 16, color: Colors.white),
                    label: const Text(
                      'Subir Archivo',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: Colors.white,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
