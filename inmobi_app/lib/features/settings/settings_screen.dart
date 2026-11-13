import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../../core/config.dart';
import '../../core/notifications/notification_service.dart';
import '../../core/theme/app_theme.dart';
import '../../core/theme/theme_controller.dart';
import '../../core/widgets/glass_nav_bar.dart';
import '../../core/widgets/motion.dart';
import '../../core/widgets/states.dart';
import '../auth/auth_service.dart';
import '../auth/login_screen.dart';
import '../contacts/contact_list_screen.dart';
import '../contracts/contract_list_screen.dart';
import '../finance/finance_screens.dart';
import '../offers/offer_screens.dart';

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
            style: FilledButton.styleFrom(backgroundColor: AppColors.accent),
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

    final sections = <Widget>[
      Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [AppColors.navy, AppColors.navyDeep],
          ),
          borderRadius: BorderRadius.circular(26),
          boxShadow: [
            BoxShadow(
              color: AppColors.navy.withValues(alpha: isDark ? 0.5 : 0.28),
              blurRadius: 26,
              offset: const Offset(0, 12),
              spreadRadius: -8,
            ),
          ],
        ),
        child: Column(
          children: [
            Row(
              children: [
                Container(
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: Colors.white.withValues(alpha: 0.25),
                      width: 2,
                    ),
                  ),
                  padding: const EdgeInsets.all(2),
                  child: InitialsAvatar(
                    text: userName,
                    size: 52,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        userName,
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w800,
                          letterSpacing: -0.4,
                          color: Colors.white,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 5),
                      Row(
                        children: [
                          Container(
                            width: 7,
                            height: 7,
                            decoration: const BoxDecoration(
                              color: Color(0xFF34D399),
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 6),
                          const Text(
                            'Sesión activa',
                            style: TextStyle(
                              fontSize: 12.5,
                              fontWeight: FontWeight.w600,
                              color: Colors.white70,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 9,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    // Rol real del usuario, sin rojo (no es una alerta).
                    color: Colors.white.withValues(alpha: 0.16),
                    borderRadius: BorderRadius.circular(100),
                  ),
                  child: Text(
                    auth.isAdmin ? 'ADMINISTRADOR' : 'ASESOR',
                    style: TextStyle(
                      fontSize: 9.5,
                      fontWeight: FontWeight.w900,
                      color: Colors.white,
                      letterSpacing: 0.7,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.10),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: Colors.white.withValues(alpha: 0.14)),
              ),
              child: Row(
                children: [
                  const Icon(
                    Icons.dns_outlined,
                    size: 15,
                    color: Colors.white70,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      AppConfig.odooServer.replaceFirst(
                        RegExp(r'^https?://'),
                        '',
                      ),
                      style: const TextStyle(
                        fontSize: 11.5,
                        fontWeight: FontWeight.w600,
                        color: Colors.white,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  Text(
                    AppConfig.odooDb,
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: Colors.white.withValues(alpha: 0.6),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
      const SizedBox(height: 22),

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
            iconColor: AppColors.navy,
            title: 'Directorio de contactos',
            subtitle: 'Propietarios, compradores y aliados',
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const ContactListScreen()),
            ),
          ),
          _SettingsTile(
            icon: Icons.description_outlined,
            iconColor: AppColors.navyLight,
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
            onTap: () => Navigator.of(
              context,
            ).push(MaterialPageRoute(builder: (_) => const OfferListScreen())),
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
            iconColor: AppColors.accent,
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

      _SectionHeader(title: 'NOTIFICACIONES Y ALERTAS'),
      const _NotificationsCard(),
      const SizedBox(height: 22),

      _SectionHeader(title: 'APARIENCIA Y TEMA'),
      const _ThemeSelectorCard(),
      const SizedBox(height: 22),

      _SectionHeader(title: 'ACERCA DE'),
      _GroupCard(
        isDark: isDark,
        children: const [
          _InfoTile(
            icon: Icons.phone_android_rounded,
            label: 'Versión de Inmobi App',
            value: '1.0.0 (Edición Oficial Inmobi)',
            isLast: true,
          ),
        ],
      ),
      const SizedBox(height: 26),

      OutlinedButton.icon(
        onPressed: () => _logout(context),
        style: OutlinedButton.styleFrom(
          padding: const EdgeInsets.symmetric(vertical: 14),
          foregroundColor: AppColors.accent,
          side: const BorderSide(color: AppColors.accent, width: 1.5),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
        ),
        icon: const Icon(Icons.logout_rounded, size: 20),
        label: const Text(
          'Cerrar sesión en este dispositivo',
          style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
        ),
      ),
    ];

    return ListView.builder(
      padding: EdgeInsets.fromLTRB(
        16,
        MediaQuery.paddingOf(context).top + 12,
        16,
        GlassNavBar.reservedHeight + 16,
      ),
      itemCount: sections.length,
      itemBuilder: (context, i) => FadeSlideIn(index: i, child: sections[i]),
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
    final colors = AppColors.of(context);
    return Container(
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkSurface : Colors.white,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: isDark ? AppColors.darkLine : colors.line),
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
    final colors = AppColors.of(context);

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
                    child: Icon(
                      icon,
                      size: 20,
                      color: isDark ? AppColors.darkNavy : iconColor,
                    ),
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
                          style: TextStyle(fontSize: 12, color: colors.muted),
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
            color: isDark ? AppColors.darkLine : colors.line,
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
    final colors = AppColors.of(context);

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
          child: Row(
            children: [
              Icon(icon, size: 20, color: AppColors.navy),
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
            color: isDark ? AppColors.darkLine : colors.line,
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
    final colors = AppColors.of(context);
    const options = [
      (ThemeMode.system, 'Automático', Icons.brightness_auto_rounded),
      (ThemeMode.light, 'Claro', Icons.light_mode_rounded),
      (ThemeMode.dark, 'Oscuro', Icons.dark_mode_rounded),
    ];

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkSurface : Colors.white,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: isDark ? AppColors.darkLine : colors.line),
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
                padding: const EdgeInsets.symmetric(
                  vertical: 12,
                  horizontal: 8,
                ),
                decoration: BoxDecoration(
                  color: selected
                      ? (isDark
                            ? AppColors.navy.withValues(alpha: 0.4)
                            : AppColors.navy.withValues(alpha: 0.08))
                      : Colors.transparent,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: selected
                        ? (isDark ? AppColors.darkNavy : AppColors.navy)
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
                          ? (isDark ? AppColors.darkNavy : AppColors.navy)
                          : const Color(0xFF64748B),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      o.$2,
                      style: TextStyle(
                        fontSize: 11.5,
                        fontWeight: selected
                            ? FontWeight.w800
                            : FontWeight.w600,
                        color: selected
                            ? (isDark ? Colors.white : AppColors.navy)
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
    final colors = AppColors.of(context);

    return Container(
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkSurface : Colors.white,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: isDark ? AppColors.darkLine : colors.line),
        boxShadow: softShadow(opacity: isDark ? 0.2 : 0.04, isDark: isDark),
      ),
      // Material propio: sin él, el efecto al tocar quedaba debajo del fondo.
      child: Material(
        type: MaterialType.transparency,
        child: SwitchListTile.adaptive(
          secondary: Container(
            padding: const EdgeInsets.all(9),
            decoration: BoxDecoration(
              color: const Color(
                0xFFF59E0B,
              ).withValues(alpha: isDark ? 0.22 : 0.1),
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
            style: TextStyle(fontSize: 12, color: colors.muted),
          ),
          value: _enabled,
          onChanged: _toggle,
        ),
      ),
    );
  }
}
