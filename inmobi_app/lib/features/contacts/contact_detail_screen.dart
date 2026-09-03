import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api/odoo_client.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/app_badge.dart';
import '../../core/widgets/expandable_section.dart';
import '../../core/widgets/states.dart';
import '../auth/auth_service.dart';
import '../documents/document_service.dart';
import '../documents/documents_section.dart';
import 'contact_form_screen.dart';
import 'contact_model.dart';
import 'contact_service.dart';

class ContactDetailScreen extends StatefulWidget {
  final int contactId;
  const ContactDetailScreen({super.key, required this.contactId});

  @override
  State<ContactDetailScreen> createState() => _ContactDetailScreenState();
}

class _ContactDetailScreenState extends State<ContactDetailScreen> {
  late final OdooClient _odoo;
  late final ContactService _service;
  Contact? _contact;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _odoo = context.read<AuthService>().odoo;
    _service = ContactService(_odoo);
    _load();
  }

  Future<void> _load() async {
    try {
      final c = await _service.detail(widget.contactId);
      if (mounted) setState(() => _contact = c);
    } catch (e) {
      if (mounted) setState(() => _error = 'No se pudo cargar el contacto.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _openEdit() async {
    final saved = await Navigator.of(context).push<bool>(
      MaterialPageRoute(builder: (_) => ContactFormScreen(existing: _contact)),
    );
    if (saved == true) _load();
  }

  Future<void> _call(String phone) async {
    final uri = Uri(scheme: 'tel', path: phone);
    if (await canLaunchUrl(uri)) await launchUrl(uri);
  }

  Future<void> _whatsapp(String phone) async {
    final digits = phone.replaceAll(RegExp(r'[^0-9]'), '');
    final uri = Uri.parse('https://wa.me/$digits');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  Future<void> _email(String email) async {
    final uri = Uri(scheme: 'mailto', path: email);
    if (await canLaunchUrl(uri)) await launchUrl(uri);
  }

  Future<void> _deleteContact() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('¿Eliminar contacto?'),
        content: Text('Se eliminará "${_contact?.name ?? 'este contacto'}". Esta acción no se puede deshacer.'),
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
      await _odoo.unlink(model: 'res.partner', id: widget.contactId);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Contacto eliminado correctamente.')),
        );
        Navigator.pop(context, true);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('No se pudo eliminar. El contacto puede tener documentos o registros asociados.'),
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Contacto'),
        actions: [
          if (_contact != null) ...[
            IconButton(
              icon: const Icon(Icons.edit_outlined),
              tooltip: 'Editar',
              onPressed: _openEdit,
            ),
            IconButton(
              icon: const Icon(Icons.delete_outline_rounded, color: Color(0xFFD81F26)),
              tooltip: 'Eliminar',
              onPressed: _deleteContact,
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
          : _buildBody(AppColors.of(context)),
    );
  }

  Widget _buildBody(AppPalette colors) {
    final c = _contact!;
    return ListView(
      padding: const EdgeInsets.all(18),
      children: [
        Row(
          children: [
            InitialsAvatar(text: c.name, size: 60, color: c.roleColor(colors)),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    c.name,
                    style: const TextStyle(
                      fontSize: 19,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: [
                      AppBadge(label: c.roleLabel, color: c.roleColor(colors)),
                      if (c.isAlliedAgency && !c.isPropertyOwner)
                        AppBadge(
                          label: 'Aliada',
                          color: colors.warning,
                        ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 18),
        if (c.bestPhone.isNotEmpty || c.email.isNotEmpty)
          Row(
            children: [
              if (c.bestPhone.isNotEmpty) ...[
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _call(c.bestPhone),
                    icon: const Icon(Icons.call, size: 17),
                    label: const Text('Llamar'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: FilledButton.icon(
                    onPressed: () => _whatsapp(c.bestPhone),
                    style: FilledButton.styleFrom(
                      backgroundColor: const Color(0xFF25D366),
                    ),
                    icon: const Icon(Icons.chat, size: 17),
                    label: const Text('WhatsApp'),
                  ),
                ),
              ],
              if (c.bestPhone.isEmpty && c.email.isNotEmpty)
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _email(c.email),
                    icon: const Icon(Icons.email_outlined, size: 17),
                    label: const Text('Enviar email'),
                  ),
                ),
            ],
          ),
        const SizedBox(height: 18),
        _InfoCard(
          rows: [
            if (c.mobile.isNotEmpty) ('Celular', c.mobile),
            if (c.phone.isNotEmpty) ('Teléfono', c.phone),
            if (c.email.isNotEmpty) ('Email', c.email),
            if (c.preferredContact.isNotEmpty)
              (
                'Prefiere',
                ContactPreferredContactStyle.label(c.preferredContact),
              ),
          ],
        ),
        if (c.propertyOwnedCount > 0 ||
            c.propertyBoughtCount > 0 ||
            c.contractCount > 0) ...[
          const SizedBox(height: 14),
          Row(
            children: [
              if (c.propertyOwnedCount > 0)
                Expanded(
                  child: _CountCard(
                    icon: Icons.home_work_outlined,
                    value: '${c.propertyOwnedCount}',
                    label: 'En propiedad',
                  ),
                ),
              if (c.propertyBoughtCount > 0) ...[
                if (c.propertyOwnedCount > 0) const SizedBox(width: 10),
                Expanded(
                  child: _CountCard(
                    icon: Icons.shopping_bag_outlined,
                    value: '${c.propertyBoughtCount}',
                    label: 'Compradas',
                  ),
                ),
              ],
              if (c.contractCount > 0) ...[
                if (c.propertyOwnedCount > 0 || c.propertyBoughtCount > 0)
                  const SizedBox(width: 10),
                Expanded(
                  child: _CountCard(
                    icon: Icons.description_outlined,
                    value: '${c.contractCount}',
                    label: 'Contratos',
                  ),
                ),
              ],
            ],
          ),
        ],
        const SizedBox(height: 18),
        ExpandableSection(
          title: 'Datos personales',
          child: _InfoCard(
            rows: [
              if (c.idNumber.isNotEmpty)
                (ContactIdTypeStyle.label(c.idType), c.idNumber),
              if (c.vat.isNotEmpty) ('RUC / NIF', c.vat),
              if (c.profession.isNotEmpty) ('Profesión', c.profession),
              if (c.function.isNotEmpty) ('Cargo', c.function),
            ],
          ),
        ),
        const SizedBox(height: 8),
        ExpandableSection(
          title: 'Dirección',
          child: _InfoCard(
            rows: [
              if (c.street.isNotEmpty) ('Calle', c.street),
              if (c.city.isNotEmpty) ('Ciudad', c.city),
            ],
          ),
        ),
        const SizedBox(height: 22),
        DocumentsSection(odoo: _odoo, owner: DocumentOwner.partner(c.id)),
      ],
    );
  }
}

class _CountCard extends StatelessWidget {
  final IconData icon;
  final String value;
  final String label;
  const _CountCard({
    required this.icon,
    required this.value,
    required this.label,
  });

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 10),
      decoration: BoxDecoration(
        color: colors.neutralBg,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        children: [
          Icon(icon, size: 18, color: colors.navy),
          const SizedBox(height: 6),
          Text(
            value,
            style: TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 16,
              color: colors.navy,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 11, color: colors.mutedLight),
          ),
        ],
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
