import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api/odoo_client.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/phone_utils.dart';
import '../../core/widgets/app_badge.dart';
import '../../core/widgets/odoo_image.dart';
import '../../core/widgets/states.dart';
import '../auth/auth_service.dart';
import '../contracts/contract_detail_screen.dart';
import '../contracts/contract_list_screen.dart';
import '../documents/document_service.dart';
import '../documents/documents_section.dart';
import '../offers/offer_model.dart';
import '../offers/offer_screens.dart';
import '../offers/offer_service.dart';
import '../properties/property_detail_screen.dart';
import '../visits/visit_detail_screen.dart';
import '../visits/visit_form_screen.dart';
import '../visits/visit_model.dart';
import '../visits/visit_service.dart';
import 'crm_stage_service.dart';
import 'interactions_section.dart';
import 'lead_form_screen.dart';
import 'lead_model.dart';
import 'stage_funnel.dart';

class LeadDetailScreen extends StatefulWidget {
  final int leadId;
  const LeadDetailScreen({super.key, required this.leadId});

  @override
  State<LeadDetailScreen> createState() => _LeadDetailScreenState();
}

class _LeadDetailScreenState extends State<LeadDetailScreen>
    with SingleTickerProviderStateMixin {
  late final OdooClient _odoo;
  late final CrmStageService _stageService;
  late final TabController _tabController;
  Lead? _lead;
  bool _loading = true;
  bool _movingStage = false;
  String? _error;
  int _refreshKey = 0;

  @override
  void initState() {
    super.initState();
    _odoo = context.read<AuthService>().odoo;
    _stageService = CrmStageService(_odoo);
    _tabController = TabController(length: 4, vsync: this);
    _load();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final rows = await _odoo.searchRead(
        model: 'crm.lead',
        domain: [
          ['id', '=', widget.leadId],
        ],
        fields: Lead.detailFields,
        limit: 1,
      );
      if (mounted) {
        setState(() {
          _lead = Lead.fromJson(rows.first);
          _refreshKey++;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _error = 'No se pudo cargar el lead.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _moveStage(CrmStage stage) async {
    setState(() => _movingStage = true);
    try {
      await _odoo.write(
        model: 'crm.lead',
        id: widget.leadId,
        values: {'stage_id': stage.id},
      );
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No se pudo mover el lead de etapa.')),
        );
      }
    } finally {
      if (mounted) setState(() => _movingStage = false);
    }
  }

  Future<void> _call(String phone) => PhoneUtils.call(phone);

  Future<void> _whatsapp(String phone) => PhoneUtils.whatsapp(phone);

  Future<void> _email(String email) async {
    final uri = Uri(scheme: 'mailto', path: email);
    if (await canLaunchUrl(uri)) await launchUrl(uri);
  }

  Future<void> _openEdit() async {
    final saved = await Navigator.of(context).push<bool>(
      MaterialPageRoute(builder: (_) => LeadFormScreen(existing: _lead)),
    );
    if (saved == true) _load();
  }

  Future<void> _editDescription(String currentDesc) async {
    final result = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => _LeadDescriptionEditSheet(
        initialDescription: currentDesc,
      ),
    );
    if (result == null) return;
    try {
      await _odoo.write(
        model: 'crm.lead',
        id: widget.leadId,
        values: {'description': result},
      );
      await _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Notas de la ficha actualizadas.'),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No se pudo guardar la nota de la ficha.')),
        );
      }
    }
  }

  Future<void> _deleteLead() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('¿Eliminar oportunidad?'),
        content: Text('Se eliminará permanentemente "${_lead?.name ?? 'este lead'}". Esta acción no se puede deshacer.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: const Color(0xFFD81F26)),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Eliminar'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await _odoo.unlink(model: 'crm.lead', id: widget.leadId);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Oportunidad eliminada correctamente.')),
        );
        Navigator.pop(context, true);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No se pudo eliminar la oportunidad.')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Oportunidad'),
        actions: [
          if (_lead != null) ...[
            IconButton(
              icon: const Icon(Icons.edit_outlined),
              tooltip: 'Editar',
              onPressed: _openEdit,
            ),
            IconButton(
              icon: const Icon(Icons.delete_outline_rounded, color: Color(0xFFD81F26)),
              tooltip: 'Eliminar',
              onPressed: _deleteLead,
            ),
          ],
        ],
        bottom: _lead == null
            ? null
            : TabBar(
                controller: _tabController,
                tabs: const [
                  Tab(text: 'Resumen'),
                  Tab(text: 'Actividad'),
                  Tab(text: 'Documentos'),
                  Tab(text: 'Negociación'),
                ],
              ),
      ),
      body: _loading
          ? const LoadingView()
          : _error != null
          ? MessageView(
              icon: Icons.error_outline,
              message: _error!,
              onRetry: _load,
            )
          : _buildBody(),
    );
  }

  Widget _buildBody() {
    final lead = _lead!;
    final currency = NumberFormat.currency(
      locale: 'es_EC',
      symbol: '\$',
      decimalDigits: 0,
    );
    // Encabezado fijo (nombre, insignias, etapa) fuera de las pestañas: es lo
    // que un asesor necesita ver siempre, sin importar en qué pestaña esté.
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(18, 16, 18, 14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Text(
                      lead.name,
                      style: const TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  // Prioridad en estrellas, igual que el widget `priority` de Odoo.
                  if (lead.priority > 0)
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: List.generate(
                        lead.priority,
                        (_) => Icon(
                          Icons.star,
                          size: 17,
                          color: AppColors.of(context).warning,
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  if (lead.isGoldenOpportunity)
                    AppBadge(
                      label: 'Oportunidad de Oro',
                      color: Colors.white,
                      background: AppColors.of(context).warning,
                      icon: Icons.workspace_premium,
                    ),
                  AppBadge(
                    label: LeadTemperatureStyle.label(lead.leadTemperature),
                    color: LeadTemperatureStyle.color(lead.leadTemperature, AppColors.of(context)),
                    icon: LeadTemperatureStyle.icon(lead.leadTemperature),
                  ),
                  AppBadge(
                    label: LeadScoreStyle.label(lead.leadScore),
                    color: LeadScoreStyle.color(lead.leadScore, AppColors.of(context)),
                  ),
                  if (lead.closingDifficulty.isNotEmpty)
                    AppBadge(
                      label: LeadClosingDifficultyStyle.label(lead.closingDifficulty),
                      color: LeadClosingDifficultyStyle.color(lead.closingDifficulty, AppColors.of(context)),
                    ),
                  if (lead.leadSourceName.isNotEmpty)
                    AppBadge(label: lead.leadSourceName, color: AppColors.of(context).mutedLight),
                ],
              ),
              const SizedBox(height: 16),
              Text(
                'Etapa',
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  fontSize: 13,
                  color: AppColors.of(context).muted,
                ),
              ),
              const SizedBox(height: 8),
              StageFunnel(
                service: _stageService,
                currentStageId: lead.stageId,
                busy: _movingStage,
                onSelect: _moveStage,
              ),
            ],
          ),
        ),
        const Divider(height: 1),
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: [
              _buildResumenTab(lead, currency),
              _buildActividadTab(lead),
              _buildDocumentosTab(lead),
              _buildNegociacionTab(lead),
            ],
          ),
        ),
      ],
    );
  }

  /// Pestaña "Resumen": lo que un asesor necesita ver primero — contacto,
  /// datos de la oportunidad, preferencias del cliente y métricas de avance.
  Widget _buildResumenTab(Lead lead, NumberFormat currency) {
    return ListView(
      padding: const EdgeInsets.all(18),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Contacto',
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 13,
                    color: AppColors.of(context).muted,
                  ),
                ),
                const SizedBox(height: 10),
                _InfoRow(
                  icon: Icons.person_outline,
                  label: lead.contactName.isEmpty ? '—' : lead.contactName,
                ),
                if (lead.partnerName.isNotEmpty)
                  _InfoRow(
                    icon: Icons.badge_outlined,
                    label: 'Contacto vinculado: ${lead.partnerName}',
                  ),
                if (lead.phone.isNotEmpty)
                  _InfoRow(icon: Icons.phone_outlined, label: lead.phone),
                if (lead.email.isNotEmpty)
                  _InfoRow(icon: Icons.email_outlined, label: lead.email),
                if (lead.phone.isNotEmpty || lead.email.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      if (lead.phone.isNotEmpty) ...[
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: () => _call(lead.phone),
                            icon: const Icon(Icons.call, size: 17),
                            label: const Text('Llamar'),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: FilledButton.icon(
                            onPressed: () => _whatsapp(lead.phone),
                            style: FilledButton.styleFrom(
                              backgroundColor: const Color(0xFF25D366),
                            ),
                            icon: const Icon(Icons.chat, size: 17),
                            label: const Text('WhatsApp'),
                          ),
                        ),
                      ] else if (lead.email.isNotEmpty)
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: () => _email(lead.email),
                            icon: const Icon(Icons.email_outlined, size: 17),
                            label: const Text('Enviar email'),
                          ),
                        ),
                    ],
                  ),
                ],
              ],
            ),
          ),
        ),
        const SizedBox(height: 14),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Oportunidad',
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 13,
                    color: AppColors.of(context).muted,
                  ),
                ),
                const SizedBox(height: 10),
                if (lead.clientBudget > 0)
                  _InfoRow(
                    icon: Icons.savings_outlined,
                    label: 'Presupuesto: ${currency.format(lead.clientBudget)}',
                  ),
                if (lead.matchPercentage > 0)
                  _InfoRow(
                    icon: Icons.percent,
                    label: 'Coincidencia: ${lead.matchPercentage}%',
                  ),
                if (lead.targetPropertyId != null) ...[
                  const SizedBox(height: 8),
                  _PropertyPreviewCard(
                    odoo: _odoo,
                    propertyId: lead.targetPropertyId!,
                    name: lead.targetPropertyName,
                  ),
                  const SizedBox(height: 8),
                  OutlinedButton.icon(
                    onPressed: () => Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => ContractListScreen(
                          propertyId: lead.targetPropertyId,
                          propertyTitle: lead.targetPropertyName,
                        ),
                      ),
                    ),
                    icon: const Icon(Icons.description_outlined, size: 17),
                    label: const Text('Ver contratos de esta propiedad'),
                  ),
                ],
              ],
            ),
          ),
        ),
        if (lead.preferredCity.isNotEmpty ||
            lead.preferredBedrooms > 0 ||
            lead.preferredMinArea > 0 ||
            lead.preferredMaxArea > 0 ||
            lead.preferredPropertyTypeName.isNotEmpty ||
            lead.clientNeeds.isNotEmpty) ...[
          const SizedBox(height: 14),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Preferencias del cliente',
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 13,
                      color: AppColors.of(context).muted,
                    ),
                  ),
                  const SizedBox(height: 10),
                  if (lead.preferredPropertyTypeName.isNotEmpty)
                    _InfoRow(
                      icon: Icons.home_work_outlined,
                      label: lead.preferredPropertyTypeName,
                    ),
                  if (lead.preferredCity.isNotEmpty)
                    _InfoRow(
                      icon: Icons.place_outlined,
                      label: lead.preferredCity,
                    ),
                  if (lead.preferredBedrooms > 0)
                    _InfoRow(
                      icon: Icons.bed_outlined,
                      label: '${lead.preferredBedrooms} habitaciones',
                    ),
                  if (lead.preferredMinArea > 0 || lead.preferredMaxArea > 0)
                    _InfoRow(
                      icon: Icons.square_foot,
                      label:
                          '${lead.preferredMinArea > 0 ? lead.preferredMinArea.toStringAsFixed(0) : '0'}'
                          ' - '
                          '${lead.preferredMaxArea > 0 ? lead.preferredMaxArea.toStringAsFixed(0) : '∞'} m²',
                    ),
                  if (lead.clientNeeds.isNotEmpty) ...[
                    const SizedBox(height: 6),
                    Text(
                      lead.clientNeeds,
                      style: const TextStyle(fontSize: 13, height: 1.4),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ],
        const SizedBox(height: 14),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Seguimiento',
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 13,
                    color: AppColors.of(context).muted,
                  ),
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: [
                    if (lead.expectedRevenue > 0)
                      _MetricChip(
                        icon: Icons.trending_up,
                        label: 'Ingreso esperado',
                        value: currency.format(lead.expectedRevenue),
                      ),
                    if (lead.expectedCommission > 0)
                      _MetricChip(
                        icon: Icons.percent,
                        label: 'Comisión esperada',
                        value: currency.format(lead.expectedCommission),
                      ),
                    if (lead.dateDeadline != null)
                      _MetricChip(
                        icon: Icons.event_outlined,
                        label: 'Cierre previsto',
                        value: DateFormat(
                          'd MMM y',
                          'es_EC',
                        ).format(lead.dateDeadline!),
                      ),
                    if (lead.completedVisitsCount > 0)
                      _MetricChip(
                        icon: Icons.home_outlined,
                        label: 'Visitas hechas',
                        value: '${lead.completedVisitsCount}',
                      ),
                    if (lead.lastActivityDays > 0)
                      _MetricChip(
                        icon: Icons.history,
                        label: 'Sin actividad',
                        value: '${lead.lastActivityDays} d',
                      ),
                    if (lead.leadVelocityDays > 0)
                      _MetricChip(
                        icon: Icons.speed,
                        label: 'Antigüedad',
                        value: '${lead.leadVelocityDays} d',
                      ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  /// Pestaña "Actividad": visitas agendadas/realizadas e interacciones.
  Widget _buildActividadTab(Lead lead) {
    return ListView(
      padding: const EdgeInsets.all(18),
      children: [
        _VisitedPropertiesSection(
          key: ValueKey('visits_${_refreshKey}_${lead.id}'),
          odoo: _odoo,
          lead: lead,
          onScheduleNew: () async {
            final saved = await Navigator.of(context).push<bool>(
              MaterialPageRoute(
                builder: (_) => VisitFormScreen(
                  initialPropertyId: lead.targetPropertyId,
                  initialPropertyName: lead.targetPropertyName,
                  initialClientId: lead.partnerId,
                  initialClientName: lead.partnerName,
                ),
              ),
            );
            if (saved == true && mounted) {
              await _load();
            }
          },
        ),
        const SizedBox(height: 22),
        InteractionsSection(
          odoo: _odoo,
          leadId: lead.id,
          partnerId: lead.partnerId,
          propertyId: lead.targetPropertyId,
        ),
      ],
    );
  }

  /// Pestaña "Documentos": notas de la ficha y archivos adjuntos.
  Widget _buildDocumentosTab(Lead lead) {
    return ListView(
      padding: const EdgeInsets.all(18),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Row(
                      children: [
                        Icon(
                          Icons.description_outlined,
                          size: 17,
                          color: Color(0xFF28235D),
                        ),
                        SizedBox(width: 8),
                        Text(
                          'Notas de la Ficha (Pestaña Notas)',
                          style: TextStyle(
                            fontWeight: FontWeight.w700,
                            fontSize: 13.5,
                          ),
                        ),
                      ],
                    ),
                    TextButton.icon(
                      onPressed: () => _editDescription(lead.description),
                      icon: Icon(
                        lead.description.isEmpty ? Icons.add_rounded : Icons.edit_outlined,
                        size: 15,
                        color: const Color(0xFFD81F26),
                      ),
                      label: Text(
                        lead.description.isEmpty ? 'Agregar' : 'Editar',
                        style: const TextStyle(
                          color: Color(0xFFD81F26),
                          fontWeight: FontWeight.w700,
                          fontSize: 12.5,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                if (lead.description.isNotEmpty)
                  SelectableText(
                    lead.description,
                    style: const TextStyle(fontSize: 13.5, height: 1.5),
                  )
                else
                  InkWell(
                    onTap: () => _editDescription(''),
                    borderRadius: BorderRadius.circular(10),
                    child: Container(
                      width: double.infinity,
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                      decoration: BoxDecoration(
                        color: AppColors.of(context).neutralBg,
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(
                          color: AppColors.of(context).line,
                        ),
                      ),
                      child: Row(
                        children: [
                          Icon(Icons.edit_note_rounded, size: 18, color: AppColors.of(context).mutedLight),
                          SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'Agregar una descripción o notas de requerimiento del lead...',
                              style: TextStyle(fontSize: 12.5, color: AppColors.of(context).mutedLight),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 22),
        DocumentsSection(odoo: _odoo, owner: DocumentOwner.lead(lead.id)),
      ],
    );
  }

  /// Pestaña "Negociación": tips de IA, ofertas y el cierre de la venta.
  Widget _buildNegociacionTab(Lead lead) {
    return ListView(
      padding: const EdgeInsets.all(18),
      children: [
        if (lead.smartNegotiationTips.isNotEmpty) ...[
          Card(
            color: AppColors.of(context).infoBg,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.auto_awesome, size: 16, color: AppColors.of(context).info),
                      SizedBox(width: 6),
                      Text(
                        'Tips de negociación (IA)',
                        style: TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    lead.smartNegotiationTips,
                    style: const TextStyle(fontSize: 13, height: 1.4),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 22),
        ],
        _LeadOffersSection(
          key: ValueKey('offers_${_refreshKey}_${lead.id}'),
          odoo: _odoo,
          lead: lead,
          onOfferChanged: _load,
        ),
        const SizedBox(height: 22),
        _LeadSaleSection(
          key: ValueKey('sale_${_refreshKey}_${lead.id}'),
          odoo: _odoo,
          lead: lead,
        ),
      ],
    );
  }
}

/// Métrica compacta del bloque de seguimiento del lead.
class _MetricChip extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  const _MetricChip({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.of(context).neutralBg,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 15, color: AppColors.of(context).navy),
          const SizedBox(width: 7),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                label,
                style: TextStyle(
                  fontSize: 10,
                  color: AppColors.of(context).mutedLight,
                ),
              ),
              Text(
                value,
                style: const TextStyle(
                  fontSize: 12.5,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String label;
  const _InfoRow({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        children: [
          Icon(icon, size: 17, color: AppColors.of(context).navy),
          const SizedBox(width: 10),
          Expanded(child: Text(label, style: const TextStyle(fontSize: 13.5))),
        ],
      ),
    );
  }
}

class _PropertyPreviewCard extends StatelessWidget {
  final OdooClient odoo;
  final int propertyId;
  final String name;
  const _PropertyPreviewCard({
    required this.odoo,
    required this.propertyId,
    required this.name,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: () => Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => PropertyDetailScreen(propertyId: propertyId),
        ),
      ),
      child: Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          border: Border.all(color: AppColors.of(context).line),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: SizedBox(
                width: 52,
                height: 52,
                child: OdooImage(
                  odoo: odoo,
                  model: 'estate.property',
                  id: propertyId,
                  field: 'image_main',
                  width: 120,
                  height: 120,
                ),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                name,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontWeight: FontWeight.w600,
                  fontSize: 13,
                ),
              ),
            ),
            Icon(Icons.chevron_right, color: AppColors.of(context).mutedLight),
          ],
        ),
      ),
    );
  }
}

/// Sección que muestra todas las propiedades visitadas o citas del lead
class _VisitedPropertiesSection extends StatefulWidget {
  final OdooClient odoo;
  final Lead lead;
  final VoidCallback onScheduleNew;

  const _VisitedPropertiesSection({
    super.key,
    required this.odoo,
    required this.lead,
    required this.onScheduleNew,
  });

  @override
  State<_VisitedPropertiesSection> createState() => _VisitedPropertiesSectionState();
}

class _VisitedPropertiesSectionState extends State<_VisitedPropertiesSection> {
  late final VisitService _visitService;
  List<Visit> _visits = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _visitService = VisitService(widget.odoo);
    _loadVisits();
  }

  @override
  void didUpdateWidget(covariant _VisitedPropertiesSection oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.lead.id != widget.lead.id || oldWidget.lead.partnerId != widget.lead.partnerId) {
      _loadVisits();
    }
  }

  Future<void> _loadVisits() async {
    setState(() => _loading = true);
    try {
      final visits = await _visitService.listForLead(
        leadId: widget.lead.id,
        partnerId: widget.lead.partnerId,
        propertyId: widget.lead.targetPropertyId,
      );
      if (mounted) setState(() => _visits = visits);
    } catch (_) {
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final dateFmt = DateFormat('d MMM yyyy · HH:mm', 'es_EC');

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(
                  Icons.tour_outlined,
                  size: 18,
                  color: Color(0xFF28235D),
                ),
                const SizedBox(width: 8),
                const Expanded(
                  child: Text(
                    'Propiedades Visitadas y Citas',
                    style: TextStyle(
                      fontWeight: FontWeight.w800,
                      fontSize: 14,
                    ),
                  ),
                ),
                IconButton(
                  visualDensity: VisualDensity.compact,
                  tooltip: 'Agendar nueva visita',
                  onPressed: widget.onScheduleNew,
                  icon: const Icon(
                    Icons.add_circle_outline_rounded,
                    color: Color(0xFFD81F26),
                    size: 20,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),

            if (_loading)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: SizedBox(
                    width: 24,
                    height: 24,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                ),
              )
            else if (_visits.isEmpty)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF1E1A3E) : AppColors.of(context).neutralBg,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: isDark ? Colors.white12 : AppColors.of(context).line,
                  ),
                ),
                child: Column(
                  children: [
                    Icon(
                      Icons.home_work_outlined,
                      size: 32,
                      color: AppColors.of(context).mutedLight,
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'No hay visitas registradas para este cliente.',
                      style: TextStyle(
                        fontSize: 12.5,
                        color: AppColors.of(context).muted,
                        fontWeight: FontWeight.w500,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 10),
                    OutlinedButton.icon(
                      onPressed: widget.onScheduleNew,
                      style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10),
                        ),
                      ),
                      icon: const Icon(Icons.add, size: 16),
                      label: const Text('Agendar Primera Visita', style: TextStyle(fontSize: 12)),
                    ),
                  ],
                ),
              )
            else
              ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: _visits.length,
                separatorBuilder: (_, _) => const SizedBox(height: 10),
                itemBuilder: (context, i) {
                  final v = _visits[i];
                  final stateColor = VisitStateStyle.color(v.visitState, AppColors.of(context));
                  final hasProperty = v.propertyId != null;

                  return Container(
                    decoration: BoxDecoration(
                      color: isDark ? const Color(0xFF1E1A3E) : Colors.white,
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(
                        color: isDark ? Colors.white12 : AppColors.of(context).line,
                      ),
                    ),
                    child: Material(
                      color: Colors.transparent,
                      child: InkWell(
                        borderRadius: BorderRadius.circular(14),
                        onTap: () => Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => VisitDetailScreen(visitId: v.id),
                          ),
                        ).then((_) => _loadVisits()),
                        child: Padding(
                          padding: const EdgeInsets.all(12),
                          child: Row(
                            children: [
                              // Miniatura o Icono
                              ClipRRect(
                                borderRadius: BorderRadius.circular(10),
                                child: SizedBox(
                                  width: 48,
                                  height: 48,
                                  child: hasProperty
                                      ? OdooImage(
                                          odoo: widget.odoo,
                                          model: 'estate.property',
                                          id: v.propertyId!,
                                          field: 'image_main',
                                          width: 100,
                                          height: 100,
                                          errorBuilder: (_) => Container(
                                            color: AppColors.of(context).navy.withValues(alpha: 0.08),
                                            child: Icon(
                                              Icons.home_work_outlined,
                                              size: 24,
                                              color: AppColors.of(context).navy,
                                            ),
                                          ),
                                        )
                                      : Container(
                                          color: AppColors.of(context).navy.withValues(alpha: 0.08),
                                          child: Icon(
                                            Icons.calendar_today_rounded,
                                            size: 22,
                                            color: AppColors.of(context).navy,
                                          ),
                                        ),
                                ),
                              ),
                              const SizedBox(width: 12),

                              // Info
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      v.propertyName.isNotEmpty
                                          ? v.propertyName
                                          : v.name,
                                      style: const TextStyle(
                                        fontWeight: FontWeight.w700,
                                        fontSize: 13.5,
                                      ),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                    const SizedBox(height: 3),
                                    Row(
                                      children: [
                                        Icon(
                                          Icons.access_time_rounded,
                                          size: 13,
                                          color: AppColors.of(context).mutedLight,
                                        ),
                                        const SizedBox(width: 4),
                                        Text(
                                          dateFmt.format(v.start),
                                          style: TextStyle(
                                            fontSize: 11.5,
                                            color: AppColors.of(context).muted,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ],
                                ),
                              ),

                              // Badge de Estado
                              AppBadge(
                                label: VisitStateStyle.label(v.visitState),
                                color: stateColor,
                                background: stateColor.withValues(alpha: 0.12),
                              ),
                            ],
                          ),
                        ),
                      ),
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

/// Modal para editar la descripción y notas de la ficha del Lead (pestaña Notas de Odoo)
class _LeadDescriptionEditSheet extends StatefulWidget {
  final String initialDescription;
  const _LeadDescriptionEditSheet({required this.initialDescription});

  @override
  State<_LeadDescriptionEditSheet> createState() => _LeadDescriptionEditSheetState();
}

class _LeadDescriptionEditSheetState extends State<_LeadDescriptionEditSheet> {
  late final TextEditingController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = TextEditingController(text: widget.initialDescription);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF14112E) : Colors.white,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      ),
      padding: EdgeInsets.fromLTRB(
        20,
        14,
        20,
        MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      child: SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 38,
                height: 4,
                decoration: BoxDecoration(
                  color: isDark ? Colors.white24 : Colors.grey[300],
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Row(
                  children: [
                    Icon(
                      Icons.description_outlined,
                      size: 20,
                      color: Color(0xFF28235D),
                    ),
                    SizedBox(width: 8),
                    Text(
                      'Notas de la Ficha del Lead',
                      style: TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ],
                ),
                IconButton(
                  icon: const Icon(Icons.close_rounded, size: 20),
                  onPressed: () => Navigator.pop(context),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              'Esta nota se guarda directamente en la pestaña "Notas" del formulario del lead en Odoo.',
              style: TextStyle(fontSize: 12, color: AppColors.of(context).muted),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: _ctrl,
              maxLines: 7,
              autofocus: true,
              style: const TextStyle(fontSize: 14, height: 1.4),
              decoration: const InputDecoration(
                hintText: 'Escribe aquí la descripción, acuerdos o notas del cliente...',
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.all(Radius.circular(12)),
                ),
              ),
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              height: 46,
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF28235D),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                onPressed: () => Navigator.pop(context, _ctrl.text.trim()),
                child: const Text(
                  'Guardar Nota en la Ficha',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w800,
                    color: Colors.white,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Sección de Ofertas Comerciales asociadas al Lead
class _LeadOffersSection extends StatefulWidget {
  final OdooClient odoo;
  final Lead lead;
  final VoidCallback onOfferChanged;

  const _LeadOffersSection({
    super.key,
    required this.odoo,
    required this.lead,
    required this.onOfferChanged,
  });

  @override
  State<_LeadOffersSection> createState() => _LeadOffersSectionState();
}

class _LeadOffersSectionState extends State<_LeadOffersSection> {
  late final OfferService _service;
  List<Offer> _offers = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _service = OfferService(widget.odoo);
    _loadOffers();
  }

  @override
  void didUpdateWidget(covariant _LeadOffersSection oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.lead.id != widget.lead.id) {
      _loadOffers();
    }
  }

  Future<void> _loadOffers() async {
    setState(() => _loading = true);
    try {
      final rows = await _service.list(leadId: widget.lead.id);
      if (mounted) setState(() => _offers = rows);
    } catch (_) {
      if (mounted) setState(() => _offers = []);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _openNewOffer() async {
    final saved = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => OfferFormScreen(
          initialLeadId: widget.lead.id,
          initialPropertyId: widget.lead.targetPropertyId,
          initialPropertyName: widget.lead.targetPropertyName,
          initialPartnerId: widget.lead.partnerId,
          initialPartnerName: widget.lead.partnerName,
        ),
      ),
    );
    if (saved == true) {
      _loadOffers();
      widget.onOfferChanged();
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final currency = NumberFormat.currency(
      locale: 'es_EC',
      symbol: '\$',
      decimalDigits: 0,
    );

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(
                  Icons.handshake_outlined,
                  size: 18,
                  color: Color(0xFF28235D),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Ofertas Comerciales (${_offers.length})',
                    style: const TextStyle(
                      fontWeight: FontWeight.w800,
                      fontSize: 14,
                    ),
                  ),
                ),
                IconButton(
                  visualDensity: VisualDensity.compact,
                  tooltip: 'Registrar nueva oferta',
                  onPressed: _openNewOffer,
                  icon: const Icon(
                    Icons.add_circle_outline_rounded,
                    color: Color(0xFFD81F26),
                    size: 20,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            if (_loading)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: SizedBox(
                    width: 24,
                    height: 24,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                ),
              )
            else if (_offers.isEmpty)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF1E1A3E) : AppColors.of(context).neutralBg,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: isDark ? Colors.white12 : AppColors.of(context).line,
                  ),
                ),
                child: Column(
                  children: [
                    Icon(
                      Icons.handshake_outlined,
                      size: 32,
                      color: AppColors.of(context).mutedLight,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'No hay ofertas registradas para este lead.',
                      style: TextStyle(
                        fontSize: 12.5,
                        color: AppColors.of(context).muted,
                        fontWeight: FontWeight.w600,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 12),
                    ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF28235D),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 9,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10),
                        ),
                      ),
                      onPressed: _openNewOffer,
                      icon: const Icon(Icons.add_rounded, size: 16, color: Colors.white),
                      label: const Text(
                        'Registrar Oferta',
                        style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: Colors.white),
                      ),
                    ),
                  ],
                ),
              )
            else
              ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: _offers.length,
                separatorBuilder: (_, _) => const SizedBox(height: 8),
                itemBuilder: (context, i) {
                  final o = _offers[i];
                  return Container(
                    decoration: BoxDecoration(
                      color: isDark ? const Color(0xFF1E1A3E) : Colors.white,
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(
                        color: isDark ? Colors.white12 : AppColors.of(context).line,
                      ),
                    ),
                    child: Material(
                      color: Colors.transparent,
                      child: InkWell(
                        borderRadius: BorderRadius.circular(14),
                        onTap: () => Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => OfferFormScreen(existing: o),
                          ),
                        ).then((_) {
                          _loadOffers();
                          widget.onOfferChanged();
                        }),
                        child: Padding(
                          padding: const EdgeInsets.all(12),
                          child: Row(
                            children: [
                              Container(
                                width: 44,
                                height: 44,
                                decoration: BoxDecoration(
                                  color: OfferStateStyle.color(o.state, AppColors.of(context)).withValues(alpha: 0.12),
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: Icon(
                                  Icons.savings_outlined,
                                  color: OfferStateStyle.color(o.state, AppColors.of(context)),
                                  size: 22,
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      currency.format(o.offerAmount),
                                      style: const TextStyle(
                                        fontWeight: FontWeight.w800,
                                        fontSize: 14.5,
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      o.propertyName.isNotEmpty ? o.propertyName : 'Propiedad #${o.propertyId ?? ''}',
                                      style: TextStyle(
                                        fontSize: 12,
                                        color: AppColors.of(context).muted,
                                      ),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ],
                                ),
                              ),
                              AppBadge(
                                label: OfferStateStyle.label(o.state),
                                color: OfferStateStyle.color(o.state, AppColors.of(context)),
                              ),
                            ],
                          ),
                        ),
                      ),
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

/// Sección que muestra la Venta / Negocio Cerrado vinculado al Lead (sale.order / estate.contract)
class _LeadSaleSection extends StatefulWidget {
  final OdooClient odoo;
  final Lead lead;

  const _LeadSaleSection({
    super.key,
    required this.odoo,
    required this.lead,
  });

  @override
  State<_LeadSaleSection> createState() => _LeadSaleSectionState();
}

class _LeadSaleSectionState extends State<_LeadSaleSection> {
  List<Map<String, dynamic>> _saleOrders = [];
  List<Map<String, dynamic>> _contracts = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadSales();
  }

  @override
  void didUpdateWidget(covariant _LeadSaleSection oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.lead.id != widget.lead.id) {
      _loadSales();
    }
  }

  Future<void> _loadSales() async {
    setState(() => _loading = true);
    try {
      // 1. Buscar órdenes de venta vinculadas al lead
      final List<dynamic> saleDomain = [
        '|',
        ['lead_id', '=', widget.lead.id],
        ['opportunity_id', '=', widget.lead.id],
      ];

      var orders = await widget.odoo.searchRead(
        model: 'sale.order',
        domain: saleDomain,
        fields: [
          'name',
          'amount_total',
          'amount_untaxed',
          'amount_tax',
          'state',
          'date_order',
          'partner_id',
          'user_id',
          'invoice_status',
          'client_order_ref',
        ],
        order: 'id desc',
      );

      // 2. Si no encontró por lead_id directo, buscar por partner si está presente
      if (orders.isEmpty && widget.lead.partnerId != null) {
        final List<dynamic> fallbackDomain = [
          ['partner_id', '=', widget.lead.partnerId],
        ];
        try {
          final fallback = await widget.odoo.searchRead(
            model: 'sale.order',
            domain: fallbackDomain,
            fields: [
              'name',
              'amount_total',
              'amount_untaxed',
              'amount_tax',
              'state',
              'date_order',
              'partner_id',
              'user_id',
              'invoice_status',
              'client_order_ref',
            ],
            order: 'id desc',
          );
          orders = fallback;
        } catch (_) {}
      }

      // 3. Buscar contratos vinculados
      List<Map<String, dynamic>> contracts = [];
      try {
        final List<dynamic> contractDomain = [];
        if (widget.lead.partnerId != null) {
          contractDomain.add(['partner_id', '=', widget.lead.partnerId]);
        }
        if (widget.lead.targetPropertyId != null) {
          contractDomain.add(['property_id', '=', widget.lead.targetPropertyId]);
        }
        if (contractDomain.isNotEmpty) {
          contracts = await widget.odoo.searchRead(
            model: 'estate.contract',
            domain: contractDomain,
            fields: [
              'name',
              'contract_type',
              'state',
              'amount',
              'date_start',
              'date_end',
              'partner_id',
              'property_id',
            ],
            order: 'id desc',
          );
        }
      } catch (_) {}

      if (mounted) {
        setState(() {
          _saleOrders = orders;
          _contracts = contracts;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _saleOrders = [];
          _contracts = [];
        });
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _showSaleDetails(Map<String, dynamic> order) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => _SaleOrderDetailSheet(
        odoo: widget.odoo,
        order: order,
        lead: widget.lead,
        linkedContractId: _contracts.isNotEmpty ? _contracts.first['id'] as int? : null,
      ),
    );
  }

  static String _formatState(String? state) {
    switch (state) {
      case 'sale':
        return 'Venta Confirmada';
      case 'done':
        return 'Cerrado / Bloqueado';
      case 'draft':
        return 'Presupuesto';
      case 'sent':
        return 'Presupuesto Enviado';
      case 'cancel':
        return 'Cancelado';
      default:
        return state ?? 'Borrador';
    }
  }

  static Color _stateColor(String? state) {
    switch (state) {
      case 'sale':
      case 'done':
        return const Color(0xFF10B981);
      case 'draft':
      case 'sent':
        return const Color(0xFFF59E0B);
      case 'cancel':
        return const Color(0xFFEF4444);
      default:
        return const Color(0xFF6B7280);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final currency = NumberFormat.currency(
      locale: 'es_EC',
      symbol: '\$',
      decimalDigits: 0,
    );

    if (_loading) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(7),
                    decoration: BoxDecoration(
                      color: const Color(0xFF10B981).withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(
                      Icons.verified_rounded,
                      color: Color(0xFF10B981),
                      size: 20,
                    ),
                  ),
                  const SizedBox(width: 10),
                  const Text(
                    'Venta & Negocio Cerrado',
                    style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              const Center(
                child: Padding(
                  padding: EdgeInsets.symmetric(vertical: 8),
                  child: LinearProgressIndicator(),
                ),
              ),
            ],
          ),
        ),
      );
    }

    if (_saleOrders.isEmpty && _contracts.isEmpty) {
      return const SizedBox.shrink();
    }

    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(
          color: const Color(0xFF10B981).withValues(alpha: 0.4),
          width: 1.5,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: const Color(0xFF10B981).withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(
                    Icons.verified_rounded,
                    color: Color(0xFF10B981),
                    size: 22,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Negocio Cerrado / Venta Vinculada',
                        style: TextStyle(
                          fontWeight: FontWeight.w800,
                          fontSize: 14.5,
                          color: Color(0xFF10B981),
                        ),
                      ),
                      Text(
                        'Detalles del cierre comercial en Odoo',
                        style: TextStyle(fontSize: 11.5, color: AppColors.of(context).muted),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: _saleOrders.length,
              separatorBuilder: (_, _) => const SizedBox(height: 10),
              itemBuilder: (context, i) {
                final order = _saleOrders[i];
                final orderName = (order['name'] ?? 'Venta').toString();
                final double total = (order['amount_total'] as num?)?.toDouble() ?? 0.0;
                final state = order['state']?.toString();
                final stateColor = _stateColor(state);

                return Container(
                  decoration: BoxDecoration(
                    color: isDark ? const Color(0xFF1E1A3E) : const Color(0xFFF0FDF4),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: isDark
                          ? Colors.white12
                          : const Color(0xFF10B981).withValues(alpha: 0.3),
                    ),
                  ),
                  child: Material(
                    color: Colors.transparent,
                    child: InkWell(
                      borderRadius: BorderRadius.circular(14),
                      onTap: () => _showSaleDetails(order),
                      child: Padding(
                        padding: const EdgeInsets.all(14),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Text(
                                  orderName,
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w800,
                                    fontSize: 15,
                                  ),
                                ),
                                const Spacer(),
                                AppBadge(
                                  label: _formatState(state),
                                  color: stateColor,
                                  background: stateColor.withValues(alpha: 0.12),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      'Monto Total Venta',
                                      style: TextStyle(
                                        fontSize: 11,
                                        color: AppColors.of(context).muted,
                                      ),
                                    ),
                                    Text(
                                      currency.format(total),
                                      style: const TextStyle(
                                        fontWeight: FontWeight.w900,
                                        fontSize: 18,
                                        color: Color(0xFF10B981),
                                      ),
                                    ),
                                  ],
                                ),
                                FilledButton.icon(
                                  style: FilledButton.styleFrom(
                                    backgroundColor: const Color(0xFF10B981),
                                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(10),
                                    ),
                                  ),
                                  onPressed: () => _showSaleDetails(order),
                                  icon: const Icon(Icons.visibility_outlined, size: 16),
                                  label: const Text(
                                    'Ver Detalles',
                                    style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                );
              },
            ),
            if (_contracts.isNotEmpty) ...[
              const SizedBox(height: 12),
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                onPressed: () {
                  final contractId = _contracts.first['id'] as int;
                  Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => ContractDetailScreen(contractId: contractId),
                    ),
                  );
                },
                icon: const Icon(Icons.assignment_outlined, size: 18, color: Color(0xFF28235D)),
                label: Text(
                  'Ver Contrato Formal (${_contracts.first['name'] ?? ''})',
                  style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Modal detallado del Negocio / Orden de Venta cerrada en Odoo
class _SaleOrderDetailSheet extends StatefulWidget {
  final OdooClient odoo;
  final Map<String, dynamic> order;
  final Lead lead;
  final int? linkedContractId;

  const _SaleOrderDetailSheet({
    required this.odoo,
    required this.order,
    required this.lead,
    this.linkedContractId,
  });

  @override
  State<_SaleOrderDetailSheet> createState() => _SaleOrderDetailSheetState();
}

class _SaleOrderDetailSheetState extends State<_SaleOrderDetailSheet> {
  Map<String, dynamic>? _propertyDeal;
  bool _loadingDeal = false;

  @override
  void initState() {
    super.initState();
    _loadPropertyDeal();
  }

  Future<void> _loadPropertyDeal() async {
    final propId = widget.lead.targetPropertyId;
    if (propId == null) return;
    setState(() => _loadingDeal = true);
    try {
      final rows = await widget.odoo.searchRead(
        model: 'estate.property',
        domain: [
          ['id', '=', propId],
        ],
        fields: [
          'title',
          'deal_deadline',
          'deal_earnest_amount',
          'deal_earnest_received_by_agency',
          'deal_earnest_received_by_owner',
          'deal_earnest_received_by_proxy',
          'deal_earnest_payment_cash',
          'deal_earnest_payment_transfer',
          'deal_earnest_payment_deposit',
          'deal_earnest_payment_other_check',
          'deal_earnest_payment_other',
          'deal_payment_type',
          'deal_payment_details',
          'deal_credit_institution',
          'deal_credit_advisor',
          'deal_credit_advisor_phone',
          'deal_observations',
          'deal_lead_origin',
          'date_sold',
          'sold_by',
        ],
        limit: 1,
      );
      if (rows.isNotEmpty && mounted) {
        setState(() => _propertyDeal = rows.first);
      }
    } catch (_) {
    } finally {
      if (mounted) setState(() => _loadingDeal = false);
    }
  }

  static String _paymentTypeLabel(String? type) {
    switch (type) {
      case 'cash':
        return 'Contado / Efectivo';
      case 'credit':
        return 'Crédito Hipotecario';
      case 'mixed':
        return 'Mixto (Entrada + Crédito)';
      case 'installments':
        return 'Cuotas Directas';
      default:
        return type ?? 'No especificado';
    }
  }

  static String _soldByLabel(String? s) {
    switch (s) {
      case 'agency':
        return 'Agencia Inmobiliaria';
      case 'owner':
        return 'Trato Directo / Dueño';
      case 'external':
        return 'Asesor Externo';
      default:
        return s ?? 'Agencia';
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final currency = NumberFormat.currency(
      locale: 'es_EC',
      symbol: '\$',
      decimalDigits: 2,
    );

    final order = widget.order;
    final lead = widget.lead;
    final orderName = (order['name'] ?? 'Venta').toString();
    final double total = (order['amount_total'] as num?)?.toDouble() ?? 0.0;
    final double untaxed = (order['amount_untaxed'] as num?)?.toDouble() ?? 0.0;
    final double tax = (order['amount_tax'] as num?)?.toDouble() ?? 0.0;
    final state = order['state']?.toString();
    final partnerName = order['partner_id'] is List ? order['partner_id'][1]?.toString() ?? '' : '';
    final advisorName = order['user_id'] is List ? order['user_id'][1]?.toString() ?? '' : '';
    final dateRaw = order['date_order']?.toString();
    final DateTime? date = dateRaw != null ? DateTime.tryParse(dateRaw) : null;
    final invoiceStatus = order['invoice_status']?.toString() ?? '';

    // Datos del negocio cerrado en la propiedad
    final deal = _propertyDeal;
    final double earnestAmount = (deal?['deal_earnest_amount'] as num?)?.toDouble() ?? 0.0;
    final earnestAgency = deal?['deal_earnest_received_by_agency'] == true;
    final earnestOwner = deal?['deal_earnest_received_by_owner'] == true;
    final earnestProxy = deal?['deal_earnest_received_by_proxy'] == true;
    final earnestCash = deal?['deal_earnest_payment_cash'] == true;
    final earnestTransfer = deal?['deal_earnest_payment_transfer'] == true;
    final earnestDeposit = deal?['deal_earnest_payment_deposit'] == true;
    final earnestOtherCheck = deal?['deal_earnest_payment_other_check'] == true;
    final earnestOtherDesc = deal?['deal_earnest_payment_other']?.toString() ?? '';

    final paymentType = deal?['deal_payment_type']?.toString();
    final paymentDetails = deal?['deal_payment_details']?.toString() ?? '';
    final creditInst = deal?['deal_credit_institution']?.toString() ?? '';
    final creditAdvisor = deal?['deal_credit_advisor']?.toString() ?? '';
    final creditAdvisorPhone = deal?['deal_credit_advisor_phone']?.toString() ?? '';
    final deadlineRaw = deal?['deal_deadline']?.toString();
    final DateTime? deadline = deadlineRaw != null ? DateTime.tryParse(deadlineRaw) : null;
    final observations = deal?['deal_observations']?.toString() ?? '';
    final soldBy = deal?['sold_by']?.toString();

    // Recopilar receptores de seña
    final List<String> receivers = [];
    if (earnestAgency) receivers.add('Inmobiliaria');
    if (earnestOwner) receivers.add('Propietario');
    if (earnestProxy) receivers.add('Apoderado');

    // Recopilar medios de pago de seña
    final List<String> earnestMethods = [];
    if (earnestCash) earnestMethods.add('Efectivo');
    if (earnestTransfer) earnestMethods.add('Transferencia');
    if (earnestDeposit) earnestMethods.add('Depósito');
    if (earnestOtherCheck) {
      earnestMethods.add(earnestOtherDesc.isNotEmpty ? 'Otro ($earnestOtherDesc)' : 'Otro');
    }

    return Container(
      constraints: BoxConstraints(
        maxHeight: MediaQuery.of(context).size.height * 0.9,
      ),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF14112E) : Colors.white,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      ),
      padding: EdgeInsets.fromLTRB(
        20,
        14,
        20,
        MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      child: SafeArea(
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 38,
                  height: 4,
                  decoration: BoxDecoration(
                    color: isDark ? Colors.white24 : Colors.grey[300],
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              if (_loadingDeal) ...[
                const SizedBox(height: 8),
                const LinearProgressIndicator(minHeight: 2),
              ],
              const SizedBox(height: 16),
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: const Color(0xFF10B981).withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(
                      Icons.receipt_long_rounded,
                      color: Color(0xFF10B981),
                      size: 24,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Orden de Venta $orderName',
                          style: const TextStyle(
                            fontSize: 17,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        Text(
                          _LeadSaleSectionState._formatState(state),
                          style: TextStyle(
                            fontSize: 12.5,
                            fontWeight: FontWeight.w600,
                            color: _LeadSaleSectionState._stateColor(state),
                          ),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close_rounded),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
              const SizedBox(height: 18),

              // Tarjeta de Montos Principales
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF1E1A3E) : const Color(0xFFF8FAFC),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: isDark ? Colors.white12 : const Color(0xFFE2E8F0),
                  ),
                ),
                child: Column(
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text('Monto Base (Subtotal)', style: TextStyle(fontSize: 13, color: AppColors.of(context).muted)),
                        Text(currency.format(untaxed), style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                      ],
                    ),
                    if (tax > 0) ...[
                      const SizedBox(height: 6),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text('Impuestos (IVA)', style: TextStyle(fontSize: 13, color: AppColors.of(context).muted)),
                          Text(currency.format(tax), style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                        ],
                      ),
                    ],
                    const Divider(height: 18),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'Total de la Venta',
                          style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        Text(
                          currency.format(total),
                          style: const TextStyle(
                            fontSize: 19,
                            fontWeight: FontWeight.w900,
                            color: Color(0xFF10B981),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),

              // Datos del Cliente y Asesor
              _InfoRow(
                icon: Icons.person_outline_rounded,
                label: 'Cliente: ${partnerName.isNotEmpty ? partnerName : lead.partnerName}',
              ),
              if (advisorName.isNotEmpty)
                _InfoRow(
                  icon: Icons.badge_outlined,
                  label: 'Asesor comisionista: $advisorName',
                ),
              if (date != null)
                _InfoRow(
                  icon: Icons.calendar_today_outlined,
                  label: 'Fecha de orden: ${DateFormat('d MMMM y, HH:mm', 'es_EC').format(date)}',
                ),
              if (invoiceStatus.isNotEmpty)
                _InfoRow(
                  icon: Icons.payments_outlined,
                  label: 'Estado de facturación: $invoiceStatus',
                ),

              // ── Bloque Seña / Arras ──
              if (earnestAmount > 0 || receivers.isNotEmpty || earnestMethods.isNotEmpty) ...[
                const SizedBox(height: 16),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: isDark ? const Color(0xFF1E1A3E) : const Color(0xFFEFF6FF),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: const Color(0xFF3B82F6).withValues(alpha: 0.3),
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Row(
                        children: [
                          Icon(Icons.handshake_outlined, size: 18, color: Color(0xFF3B82F6)),
                          SizedBox(width: 8),
                          Text(
                            'Seña / Arras del Negocio',
                            style: TextStyle(
                              fontWeight: FontWeight.w800,
                              fontSize: 13.5,
                              color: Color(0xFF1D4ED8),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      if (earnestAmount > 0)
                        _InfoRow(
                          icon: Icons.attach_money_rounded,
                          label: 'Monto de Seña: ${currency.format(earnestAmount)}',
                        ),
                      if (receivers.isNotEmpty)
                        _InfoRow(
                          icon: Icons.how_to_reg_outlined,
                          label: 'Recibió: ${receivers.join(", ")}',
                        ),
                      if (earnestMethods.isNotEmpty)
                        _InfoRow(
                          icon: Icons.account_balance_wallet_outlined,
                          label: 'Medio de Pago: ${earnestMethods.join(", ")}',
                        ),
                    ],
                  ),
                ),
              ],

              // ── Bloque Forma de Pago y Crédito Hipotecario ──
              if (paymentType != null || paymentDetails.isNotEmpty || creditInst.isNotEmpty) ...[
                const SizedBox(height: 14),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: isDark ? const Color(0xFF1E1A3E) : const Color(0xFFF0FDF4),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: const Color(0xFF10B981).withValues(alpha: 0.3),
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Row(
                        children: [
                          Icon(Icons.credit_card_outlined, size: 18, color: Color(0xFF10B981)),
                          SizedBox(width: 8),
                          Text(
                            'Forma de Pago del Negocio',
                            style: TextStyle(
                              fontWeight: FontWeight.w800,
                              fontSize: 13.5,
                              color: Color(0xFF047857),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      if (paymentType != null)
                        _InfoRow(
                          icon: Icons.category_outlined,
                          label: 'Tipo: ${_paymentTypeLabel(paymentType)}',
                        ),
                      if (paymentDetails.isNotEmpty)
                        _InfoRow(
                          icon: Icons.notes_outlined,
                          label: 'Detalles de pago: $paymentDetails',
                        ),
                      if (creditInst.isNotEmpty)
                        _InfoRow(
                          icon: Icons.account_balance_outlined,
                          label: 'Institución de crédito: $creditInst',
                        ),
                      if (creditAdvisor.isNotEmpty)
                        _InfoRow(
                          icon: Icons.support_agent_outlined,
                          label: 'Asesor de crédito: $creditAdvisor ${creditAdvisorPhone.isNotEmpty ? "($creditAdvisorPhone)" : ""}',
                        ),
                    ],
                  ),
                ),
              ],

              // ── Fechas y Cerrado Por ──
              if (deadline != null || soldBy != null) ...[
                const SizedBox(height: 12),
                if (soldBy != null)
                  _InfoRow(
                    icon: Icons.business_outlined,
                    label: 'Cerrado por: ${_soldByLabel(soldBy)}',
                  ),
                if (deadline != null)
                  _InfoRow(
                    icon: Icons.event_busy_outlined,
                    label: 'Fecha límite de cierre: ${DateFormat('d MMMM y', 'es_EC').format(deadline)}',
                  ),
              ],

              // ── Observaciones del Negocio Cerrado ──
              if (observations.isNotEmpty) ...[
                const SizedBox(height: 14),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: isDark ? const Color(0xFF1E1A3E) : const Color(0xFFFFFBEB),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: const Color(0xFFF59E0B).withValues(alpha: 0.4),
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Row(
                        children: [
                          Icon(Icons.comment_outlined, size: 17, color: Color(0xFFD97706)),
                          SizedBox(width: 8),
                          Text(
                            'Observaciones del Negocio Cerrado',
                            style: TextStyle(
                              fontWeight: FontWeight.w800,
                              fontSize: 13,
                              color: Color(0xFFB45309),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text(
                        observations,
                        style: const TextStyle(fontSize: 13, height: 1.4),
                      ),
                    ],
                  ),
                ),
              ],

              const SizedBox(height: 18),

              // ── Botones de acción ──
              if (widget.linkedContractId != null) ...[
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    style: FilledButton.styleFrom(
                      backgroundColor: const Color(0xFF28235D),
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    onPressed: () {
                      Navigator.pop(context);
                      Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => ContractDetailScreen(contractId: widget.linkedContractId!),
                        ),
                      );
                    },
                    icon: const Icon(Icons.assignment_outlined, size: 18),
                    label: const Text(
                      'Ver Contrato Formal del Cierre',
                      style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5),
                    ),
                  ),
                ),
                const SizedBox(height: 10),
              ],
              if (lead.targetPropertyId != null) ...[
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    onPressed: () {
                      Navigator.pop(context);
                      Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => PropertyDetailScreen(propertyId: lead.targetPropertyId!),
                        ),
                      );
                    },
                    icon: const Icon(Icons.home_work_outlined, size: 18),
                    label: const Text(
                      'Ver Ficha de la Propiedad',
                      style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5),
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
