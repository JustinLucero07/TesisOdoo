import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api/odoo_client.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/app_badge.dart';
import '../../core/widgets/odoo_image.dart';
import '../../core/widgets/states.dart';
import '../auth/auth_service.dart';
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

class _LeadDetailScreenState extends State<LeadDetailScreen> {
  late final OdooClient _odoo;
  late final CrmStageService _stageService;
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
    _load();
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
    return ListView(
      padding: const EdgeInsets.all(18),
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
                  (_) => const Icon(
                    Icons.star,
                    size: 17,
                    color: AppColors.warning,
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
              const AppBadge(
                label: 'Oportunidad de Oro',
                color: Colors.white,
                background: AppColors.warning,
                icon: Icons.workspace_premium,
              ),
            AppBadge(
              label: LeadTemperatureStyle.label(lead.leadTemperature),
              color: LeadTemperatureStyle.color(lead.leadTemperature),
              icon: LeadTemperatureStyle.icon(lead.leadTemperature),
            ),
            AppBadge(
              label: LeadScoreStyle.label(lead.leadScore),
              color: LeadScoreStyle.color(lead.leadScore),
            ),
            if (lead.closingDifficulty.isNotEmpty)
              AppBadge(
                label: LeadClosingDifficultyStyle.label(lead.closingDifficulty),
                color: LeadClosingDifficultyStyle.color(lead.closingDifficulty),
              ),
            if (lead.leadSourceName.isNotEmpty)
              AppBadge(label: lead.leadSourceName, color: AppColors.mutedLight),
          ],
        ),
        const SizedBox(height: 18),
        const Text(
          'Etapa',
          style: TextStyle(
            fontWeight: FontWeight.w700,
            fontSize: 13,
            color: AppColors.muted,
          ),
        ),
        const SizedBox(height: 8),
        StageFunnel(
          service: _stageService,
          currentStageId: lead.stageId,
          busy: _movingStage,
          onSelect: _moveStage,
        ),
        const SizedBox(height: 18),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Contacto',
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 13,
                    color: AppColors.muted,
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
                const Text(
                  'Oportunidad',
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 13,
                    color: AppColors.muted,
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
                  const Text(
                    'Preferencias del cliente',
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 13,
                      color: AppColors.muted,
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
        if (lead.smartNegotiationTips.isNotEmpty) ...[
          const SizedBox(height: 14),
          Card(
            color: AppColors.infoBg,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.auto_awesome, size: 16, color: AppColors.info),
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
        ],
        // ── Tipo 1: Notas de la Ficha del Lead (Pestaña "Notas" de Odoo / description) ──
        const SizedBox(height: 14),
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
                        color: AppColors.neutralBg,
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(
                          color: AppColors.line,
                        ),
                      ),
                      child: const Row(
                        children: [
                          Icon(Icons.edit_note_rounded, size: 18, color: AppColors.mutedLight),
                          SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'Agregar una descripción o notas de requerimiento del lead...',
                              style: TextStyle(fontSize: 12.5, color: AppColors.mutedLight),
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
        // Seguimiento comercial: cifras que Odoo ya calcula para este lead.
        const SizedBox(height: 14),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Seguimiento',
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 13,
                    color: AppColors.muted,
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
        const SizedBox(height: 22),
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
        _LeadOffersSection(
          key: ValueKey('offers_${_refreshKey}_${lead.id}'),
          odoo: _odoo,
          lead: lead,
          onOfferChanged: _load,
        ),
        const SizedBox(height: 22),
        InteractionsSection(
          odoo: _odoo,
          leadId: lead.id,
          partnerId: lead.partnerId,
          propertyId: lead.targetPropertyId,
        ),
        const SizedBox(height: 22),
        DocumentsSection(odoo: _odoo, owner: DocumentOwner.lead(lead.id)),
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
        color: AppColors.neutralBg,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 15, color: AppColors.navy),
          const SizedBox(width: 7),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                label,
                style: const TextStyle(
                  fontSize: 10,
                  color: AppColors.mutedLight,
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
          Icon(icon, size: 17, color: AppColors.navy),
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
          border: Border.all(color: AppColors.line),
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
            const Icon(Icons.chevron_right, color: AppColors.mutedLight),
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
                  color: isDark ? const Color(0xFF1E1A3E) : AppColors.neutralBg,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: isDark ? Colors.white12 : AppColors.line,
                  ),
                ),
                child: Column(
                  children: [
                    const Icon(
                      Icons.home_work_outlined,
                      size: 32,
                      color: AppColors.mutedLight,
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'No hay visitas registradas para este cliente.',
                      style: TextStyle(
                        fontSize: 12.5,
                        color: AppColors.muted,
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
                  final stateColor = VisitStateStyle.color(v.visitState);
                  final hasProperty = v.propertyId != null;

                  return Container(
                    decoration: BoxDecoration(
                      color: isDark ? const Color(0xFF1E1A3E) : Colors.white,
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(
                        color: isDark ? Colors.white12 : AppColors.line,
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
                                            color: AppColors.navy.withValues(alpha: 0.08),
                                            child: const Icon(
                                              Icons.home_work_outlined,
                                              size: 24,
                                              color: AppColors.navy,
                                            ),
                                          ),
                                        )
                                      : Container(
                                          color: AppColors.navy.withValues(alpha: 0.08),
                                          child: const Icon(
                                            Icons.calendar_today_rounded,
                                            size: 22,
                                            color: AppColors.navy,
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
                                        const Icon(
                                          Icons.access_time_rounded,
                                          size: 13,
                                          color: AppColors.mutedLight,
                                        ),
                                        const SizedBox(width: 4),
                                        Text(
                                          dateFmt.format(v.start),
                                          style: const TextStyle(
                                            fontSize: 11.5,
                                            color: AppColors.muted,
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
            const Text(
              'Esta nota se guarda directamente en la pestaña "Notas" del formulario del lead en Odoo.',
              style: TextStyle(fontSize: 12, color: AppColors.muted),
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
                  color: isDark ? const Color(0xFF1E1A3E) : AppColors.neutralBg,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: isDark ? Colors.white12 : AppColors.line,
                  ),
                ),
                child: Column(
                  children: [
                    const Icon(
                      Icons.handshake_outlined,
                      size: 32,
                      color: AppColors.mutedLight,
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'No hay ofertas registradas para este lead.',
                      style: TextStyle(
                        fontSize: 12.5,
                        color: AppColors.muted,
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
                        color: isDark ? Colors.white12 : AppColors.line,
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
                                  color: OfferStateStyle.color(o.state).withValues(alpha: 0.12),
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: Icon(
                                  Icons.savings_outlined,
                                  color: OfferStateStyle.color(o.state),
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
                                      style: const TextStyle(
                                        fontSize: 12,
                                        color: AppColors.muted,
                                      ),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ],
                                ),
                              ),
                              AppBadge(
                                label: OfferStateStyle.label(o.state),
                                color: OfferStateStyle.color(o.state),
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

