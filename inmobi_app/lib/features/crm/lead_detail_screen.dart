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
import '../properties/property_detail_screen.dart';
import '../visits/visit_form_screen.dart';
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
      setState(() => _lead = Lead.fromJson(rows.first));
    } catch (e) {
      setState(() => _error = 'No se pudo cargar el lead.');
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Oportunidad'),
        actions: [
          if (_lead != null)
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
        const SizedBox(height: 16),
        // Agendar una visita para este lead: se precargan la propiedad de
        // interés y el contacto, que es justo lo que hay que llenar.
        SizedBox(
          width: double.infinity,
          child: OutlinedButton.icon(
            onPressed: () => Navigator.of(context)
                .push<bool>(
                  MaterialPageRoute(
                    builder: (_) => VisitFormScreen(
                      initialPropertyId: lead.targetPropertyId,
                      initialPropertyName: lead.targetPropertyName,
                      initialClientId: lead.partnerId,
                      initialClientName: lead.partnerName,
                    ),
                  ),
                )
                .then((saved) {
                  if (saved == true && mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Cita agendada.')),
                    );
                  }
                }),
            icon: const Icon(Icons.event_available_outlined, size: 18),
            label: const Text('Agendar visita'),
          ),
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
        // Notas de la oportunidad (campo "description" del CRM)
        if (lead.description.isNotEmpty) ...[
          const SizedBox(height: 14),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(
                        Icons.notes_outlined,
                        size: 16,
                        color: AppColors.navy,
                      ),
                      SizedBox(width: 6),
                      Text(
                        'Notas',
                        style: TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 13,
                          color: AppColors.muted,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  SelectableText(
                    lead.description,
                    style: const TextStyle(fontSize: 13.5, height: 1.5),
                  ),
                ],
              ),
            ),
          ),
        ],
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
