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
import 'crm_stage_service.dart';
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
        Text(
          lead.name,
          style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 10),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            AppBadge(
              label: LeadTemperatureStyle.label(lead.leadTemperature),
              color: LeadTemperatureStyle.color(lead.leadTemperature),
              icon: LeadTemperatureStyle.icon(lead.leadTemperature),
            ),
            AppBadge(
              label: LeadScoreStyle.label(lead.leadScore),
              color: LeadScoreStyle.color(lead.leadScore),
            ),
            if (lead.leadSourceName.isNotEmpty)
              AppBadge(label: lead.leadSourceName, color: AppColors.mutedLight),
          ],
        ),
        const SizedBox(height: 16),
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
        const SizedBox(height: 22),
        DocumentsSection(odoo: _odoo, owner: DocumentOwner.lead(lead.id)),
      ],
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
