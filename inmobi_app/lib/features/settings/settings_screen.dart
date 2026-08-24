import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../../core/config.dart';
import '../../core/notifications/notification_service.dart';
import '../../core/theme/app_theme.dart';
import '../../core/theme/theme_controller.dart';
import '../../core/widgets/states.dart';
import '../auth/auth_service.dart';
import '../auth/login_screen.dart';
import '../contacts/contact_list_screen.dart';
import '../contracts/contract_list_screen.dart';
import '../crm/lead_form_screen.dart';
import '../finance/finance_screens.dart';
import '../offers/offer_screens.dart';
import '../properties/property_form_screen.dart';
import '../visits/visit_form_screen.dart';

/// Pantalla y Hub de Opciones & Herramientas Ejecutivas Inmobi.
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  Future<void> _logout(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Cerrar sesión'),
        content: const Text('¿Seguro que deseas salir del Portal de Inmobi?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: const Color(0xFFD81F26)),
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Cerrar sesión'),
          ),
        ],
      ),
    );
    if (confirmed != true || !context.mounted) return;
    await context.read<AuthService>().logout();
    if (!context.mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const LoginScreen()),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthService>();
    final userName = auth.userName ?? 'Asesor Inmobi';
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 110),
      children: [
        // ── Tarjeta de Perfil de Usuario ──
        Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            color: isDark ? const Color(0xFF161330) : Colors.white,
            borderRadius: BorderRadius.circular(24),
            border: Border.all(
              color: isDark ? const Color(0xFF28244E) : AppColors.line,
            ),
            boxShadow: softShadow(opacity: isDark ? 0.2 : 0.05, isDark: isDark),
          ),
          child: Row(
            children: [
              InitialsAvatar(text: userName, size: 54),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            userName,
                            style: const TextStyle(
                              fontSize: 17,
                              fontWeight: FontWeight.w800,
                              letterSpacing: -0.3,
                            ),
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 3,
                          ),
                          decoration: BoxDecoration(
                            color: const Color(0xFFD81F26).withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: const Text(
                            'ASESOR',
                            style: TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w900,
                              color: Color(0xFFD81F26),
                              letterSpacing: 0.5,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Container(
                          width: 8,
                          height: 8,
                          decoration: const BoxDecoration(
                            color: Color(0xFF10B981),
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: 6),
                        const Text(
                          'Conectado a Inmobi',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: AppColors.muted,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 20),

        // ── Accesos de Creación Rápida ──
        _SectionHeader(title: 'ACCIONES RÁPIDAS'),
        Row(
          children: [
            Expanded(
              child: _QuickActionCard(
                icon: Icons.add_home_work_rounded,
                label: '+ Propiedad',
                color: const Color(0xFF28235D),
                isDark: isDark,
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const PropertyFormScreen()),
                ),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _QuickActionCard(
                icon: Icons.person_add_alt_1_rounded,
                label: '+ Lead / CRM',
                color: const Color(0xFFD81F26),
                isDark: isDark,
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const LeadFormScreen()),
                ),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _QuickActionCard(
                icon: Icons.event_available_rounded,
                label: '+ Cita Visita',
                color: const Color(0xFF0284C7),
                isDark: isDark,
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const VisitFormScreen()),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 22),

        // ── Gestión Comercial & Documental ──
        _SectionHeader(title: 'GESTIÓN COMERCIAL'),
        _GroupCard(
          isDark: isDark,
          children: [
            _SettingsTile(
              icon: Icons.payments_outlined,
              iconColor: const Color(0xFF10B981),
              title: 'Mis comisiones',
              subtitle: 'Valores cobrados y por liquidar',
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const CommissionListScreen()),
              ),
            ),
            _SettingsTile(
              icon: Icons.contacts_outlined,
              iconColor: const Color(0xFF28235D),
              title: 'Directorio de contactos',
              subtitle: 'Propietarios, compradores y aliados',
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const ContactListScreen()),
              ),
            ),
            _SettingsTile(
              icon: Icons.description_outlined,
              iconColor: const Color(0xFF3F3787),
              title: 'Contratos y expedientes',
              subtitle: 'Arriendos, promesas de compraventa',
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const ContractListScreen()),
              ),
            ),
            _SettingsTile(
              icon: Icons.handshake_outlined,
              iconColor: const Color(0xFF0284C7),
              title: 'Ofertas y propuestas',
              subtitle: 'Negociaciones de precio activas',
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const OfferListScreen()),
              ),
            ),
            _SettingsTile(
              icon: Icons.receipt_long_outlined,
              iconColor: const Color(0xFF6366F1),
              title: 'Cobros y pagos',
              subtitle: 'Cuotas de contratos y reservas',
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const PaymentListScreen()),
              ),
            ),
            _SettingsTile(
              icon: Icons.request_quote_outlined,
              iconColor: const Color(0xFFF59E0B),
              title: 'Gastos de propiedades',
              subtitle: 'Mantenimientos y publicidad',
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const ExpenseListScreen()),
              ),
            ),
            _SettingsTile(
              icon: Icons.assessment_outlined,
              iconColor: const Color(0xFFD81F26),
              title: 'Tasaciones y avalúos',
              subtitle: 'Informes de valoración inmobiliaria',
              isLast: true,
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const AppraisalListScreen()),
              ),
            ),
          ],
        ),
        const SizedBox(height: 22),

        // ── Notificaciones & Alertas ──
        _SectionHeader(title: 'NOTIFICACIONES Y ALERTAS'),
        const _NotificationsCard(),
        const SizedBox(height: 22),

        // ── Apariencia ──
        _SectionHeader(title: 'APARIENCIA Y TEMA'),
        const _ThemeSelectorCard(),
        const SizedBox(height: 22),

        // ── Sistema y Servidor ──
        _SectionHeader(title: 'SISTEMA Y SERVIDOR'),
        _GroupCard(
          isDark: isDark,
          children: [
            _InfoTile(
              icon: Icons.dns_outlined,
              label: 'Servidor Inmobi / Odoo',
              value: AppConfig.odooServer,
            ),
            _InfoTile(
              icon: Icons.storage_outlined,
              label: 'Base de datos',
              value: AppConfig.odooDb,
            ),
            const _InfoTile(
              icon: Icons.phone_android_rounded,
              label: 'Versión de Inmobi App',
              value: '1.0.0 (Edición Oficial Inmobi)',
              isLast: true,
            ),
          ],
        ),
        const SizedBox(height: 26),

        // ── Botón de Cerrar Sesión ──
        OutlinedButton.icon(
          onPressed: () => _logout(context),
          style: OutlinedButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 14),
            foregroundColor: const Color(0xFFD81F26),
            side: const BorderSide(color: Color(0xFFD81F26), width: 1.5),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          ),
          icon: const Icon(Icons.logout_rounded, size: 20),
          label: const Text(
            'Cerrar sesión en este dispositivo',
            style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
          ),
        ),
      ],
    );
  }
}

class _QuickActionCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final bool isDark;
  final VoidCallback onTap;

  const _QuickActionCard({
    required this.icon,
    required this.label,
    required this.color,
    required this.isDark,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: isDark ? const Color(0xFF161330) : Colors.white,
      borderRadius: BorderRadius.circular(18),
      child: InkWell(
        onTap: () {
          HapticFeedback.lightImpact();
          onTap();
        },
        borderRadius: BorderRadius.circular(18),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 8),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(18),
            border: Border.all(
              color: isDark ? const Color(0xFF28244E) : AppColors.line,
            ),
          ),
          child: Column(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: isDark ? 0.25 : 0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, color: isDark ? const Color(0xFF8B85FF) : color, size: 20),
              ),
              const SizedBox(height: 8),
              Text(
                label,
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w800,
                  color: isDark ? Colors.white : const Color(0xFF0F172A),
                ),
                textAlign: TextAlign.center,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;
  const _SectionHeader({required this.title});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 6, bottom: 8),
      child: Text(
        title,
        style: const TextStyle(
          fontWeight: FontWeight.w800,
          fontSize: 11,
          color: Color(0xFF94A3B8),
          letterSpacing: 0.8,
        ),
      ),
    );
  }
}

class _GroupCard extends StatelessWidget {
  final List<Widget> children;
  final bool isDark;
  const _GroupCard({required this.children, required this.isDark});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF161330) : Colors.white,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(
          color: isDark ? const Color(0xFF28244E) : AppColors.line,
        ),
        boxShadow: softShadow(opacity: isDark ? 0.2 : 0.04, isDark: isDark),
      ),
      child: Column(children: children),
    );
  }
}

class _SettingsTile extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final String title;
  final String subtitle;
  final VoidCallback onTap;
  final bool isLast;

  const _SettingsTile({
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.subtitle,
    required this.onTap,
    this.isLast = false,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Column(
      children: [
        Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: BorderRadius.circular(22),
            onTap: () {
              HapticFeedback.lightImpact();
              onTap();
            },
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(9),
                    decoration: BoxDecoration(
                      color: iconColor.withValues(alpha: isDark ? 0.22 : 0.1),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(icon, size: 20, color: isDark ? const Color(0xFF8B85FF) : iconColor),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          title,
                          style: const TextStyle(
                            fontWeight: FontWeight.w700,
                            fontSize: 14,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          subtitle,
                          style: const TextStyle(
                            fontSize: 12,
                            color: AppColors.muted,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const Icon(
                    Icons.chevron_right_rounded,
                    size: 20,
                    color: Color(0xFF94A3B8),
                  ),
                ],
              ),
            ),
          ),
        ),
        if (!isLast)
          Divider(
            height: 1,
            indent: 58,
            endIndent: 16,
            color: isDark ? const Color(0xFF28244E) : AppColors.line,
          ),
      ],
    );
  }
}

class _InfoTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final bool isLast;

  const _InfoTile({
    required this.icon,
    required this.label,
    required this.value,
    this.isLast = false,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
          child: Row(
            children: [
              Icon(icon, size: 20, color: const Color(0xFF28235D)),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      label,
                      style: const TextStyle(
                        fontSize: 12,
                        color: Color(0xFF94A3B8),
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      value,
                      style: const TextStyle(
                        fontSize: 13.5,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        if (!isLast)
          Divider(
            height: 1,
            indent: 50,
            endIndent: 16,
            color: isDark ? const Color(0xFF28244E) : AppColors.line,
          ),
      ],
    );
  }
}

class _ThemeSelectorCard extends StatelessWidget {
  const _ThemeSelectorCard();

  @override
  Widget build(BuildContext context) {
    final ctrl = context.watch<ThemeController>();
    final isDark = Theme.of(context).brightness == Brightness.dark;
    const options = [
      (ThemeMode.system, 'Automático', Icons.brightness_auto_rounded),
      (ThemeMode.light, 'Claro', Icons.light_mode_rounded),
      (ThemeMode.dark, 'Oscuro', Icons.dark_mode_rounded),
    ];

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF161330) : Colors.white,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(
          color: isDark ? const Color(0xFF28244E) : AppColors.line,
        ),
        boxShadow: softShadow(opacity: isDark ? 0.2 : 0.04, isDark: isDark),
      ),
      child: Row(
        children: options.map((o) {
          final selected = ctrl.mode == o.$1;

          return Expanded(
            child: GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: () {
                HapticFeedback.selectionClick();
                ctrl.setMode(o.$1);
              },
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                margin: const EdgeInsets.symmetric(horizontal: 4),
                padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
                decoration: BoxDecoration(
                  color: selected
                      ? (isDark
                          ? const Color(0xFF28235D).withValues(alpha: 0.4)
                          : const Color(0xFF28235D).withValues(alpha: 0.08))
                      : Colors.transparent,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: selected
                        ? (isDark ? const Color(0xFF8B85FF) : const Color(0xFF28235D))
                        : Colors.transparent,
                    width: 1.5,
                  ),
                ),
                child: Column(
                  children: [
                    Icon(
                      o.$3,
                      size: 22,
                      color: selected
                          ? (isDark ? const Color(0xFF8B85FF) : const Color(0xFF28235D))
                          : const Color(0xFF64748B),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      o.$2,
                      style: TextStyle(
                        fontSize: 11.5,
                        fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
                        color: selected
                            ? (isDark ? Colors.white : const Color(0xFF28235D))
                            : const Color(0xFF64748B),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}

class _NotificationsCard extends StatefulWidget {
  const _NotificationsCard();

  @override
  State<_NotificationsCard> createState() => _NotificationsCardState();
}

class _NotificationsCardState extends State<_NotificationsCard> {
  late bool _enabled = NotificationService.instance.enabled;
  int _pending = 0;

  @override
  void initState() {
    super.initState();
    _refreshPending();
  }

  Future<void> _refreshPending() async {
    final list = await NotificationService.instance.pending();
    if (mounted) setState(() => _pending = list.length);
  }

  Future<void> _toggle(bool value) async {
    if (value) {
      final granted = await NotificationService.instance.requestPermission();
      if (!granted && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Activa los permisos de notificación en los ajustes de tu teléfono.',
            ),
          ),
        );
      }
    }
    await NotificationService.instance.setEnabled(value);
    if (mounted) setState(() => _enabled = value);
    _refreshPending();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Container(
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF161330) : Colors.white,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(
          color: isDark ? const Color(0xFF28244E) : AppColors.line,
        ),
        boxShadow: softShadow(opacity: isDark ? 0.2 : 0.04, isDark: isDark),
      ),
      child: SwitchListTile.adaptive(
        secondary: Container(
          padding: const EdgeInsets.all(9),
          decoration: BoxDecoration(
            color: const Color(0xFFF59E0B).withValues(alpha: isDark ? 0.22 : 0.1),
            borderRadius: BorderRadius.circular(12),
          ),
          child: const Icon(
            Icons.notifications_active_outlined,
            color: Color(0xFFF59E0B),
            size: 20,
          ),
        ),
        title: const Text(
          'Avisos de citas y Push FCM',
          style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
        ),
        subtitle: Text(
          _enabled
              ? (_pending > 0
                  ? '$_pending cita${_pending == 1 ? '' : 's'} programada${_pending == 1 ? '' : 's'}'
                  : 'Alertas en tiempo real activas')
              : 'Desactivado',
          style: const TextStyle(fontSize: 12, color: AppColors.muted),
        ),
        value: _enabled,
        onChanged: _toggle,
      ),
    );
  }
}
