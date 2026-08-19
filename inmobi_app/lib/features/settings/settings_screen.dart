import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/config.dart';
import '../../core/notifications/notification_service.dart';
import '../../core/theme/app_theme.dart';
import '../../core/theme/theme_controller.dart';
import '../../core/widgets/states.dart';
import '../auth/auth_service.dart';
import '../auth/login_screen.dart';
import '../finance/finance_screens.dart';
import '../offers/offer_screens.dart';

/// Pantalla de Configuración — perfil del asesor, datos de conexión (solo
/// lectura) y cerrar sesión. Ocupa el lugar del Agente de IA en la
/// navegación inferior mientras no se decide si ese módulo se integra.
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  Future<void> _logout(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Cerrar sesión'),
        content: const Text('¿Seguro que quieres cerrar sesión?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Cerrar sesión'),
          ),
        ],
      ),
    );
    if (confirmed != true || !context.mounted) return;
    context.read<AuthService>().logout();
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const LoginScreen()),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthService>();
    final userName = auth.userName ?? '';

    return ListView(
      padding: const EdgeInsets.all(18),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Row(
              children: [
                InitialsAvatar(text: userName, size: 54),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        userName,
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 3),
                      const Text(
                        'Asesor inmobiliario',
                        style: TextStyle(
                          fontSize: 12.5,
                          color: AppColors.muted,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 22),
        const Text(
          'Mi trabajo',
          style: TextStyle(
            fontWeight: FontWeight.w700,
            fontSize: 13,
            color: AppColors.muted,
          ),
        ),
        const SizedBox(height: 8),
        Card(
          child: Column(
            children: [
              ListTile(
                leading: const Icon(
                  Icons.payments_outlined,
                  color: AppColors.navy,
                ),
                title: const Text('Mis comisiones'),
                subtitle: const Text('Cobrado y por cobrar'),
                trailing: const Icon(
                  Icons.chevron_right,
                  color: AppColors.mutedLight,
                ),
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => const CommissionListScreen(),
                  ),
                ),
              ),
              const Divider(height: 1),
              ListTile(
                leading: const Icon(
                  Icons.handshake_outlined,
                  color: AppColors.navy,
                ),
                title: const Text('Ofertas'),
                subtitle: const Text('Negociaciones en curso'),
                trailing: const Icon(
                  Icons.chevron_right,
                  color: AppColors.mutedLight,
                ),
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const OfferListScreen()),
                ),
              ),
              const Divider(height: 1),
              ListTile(
                leading: const Icon(
                  Icons.receipt_long_outlined,
                  color: AppColors.navy,
                ),
                title: const Text('Pagos'),
                subtitle: const Text('Cuotas y cobros de contratos'),
                trailing: const Icon(
                  Icons.chevron_right,
                  color: AppColors.mutedLight,
                ),
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const PaymentListScreen()),
                ),
              ),
              const Divider(height: 1),
              ListTile(
                leading: const Icon(
                  Icons.request_quote_outlined,
                  color: AppColors.navy,
                ),
                title: const Text('Gastos'),
                subtitle: const Text('Gastos imputados a propiedades'),
                trailing: const Icon(
                  Icons.chevron_right,
                  color: AppColors.mutedLight,
                ),
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const ExpenseListScreen()),
                ),
              ),
              const Divider(height: 1),
              ListTile(
                leading: const Icon(
                  Icons.assessment_outlined,
                  color: AppColors.navy,
                ),
                title: const Text('Tasaciones'),
                subtitle: const Text('Avalúos solicitados'),
                trailing: const Icon(
                  Icons.chevron_right,
                  color: AppColors.mutedLight,
                ),
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => const AppraisalListScreen(),
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 22),
        const Text(
          'Notificaciones',
          style: TextStyle(
            fontWeight: FontWeight.w700,
            fontSize: 13,
            color: AppColors.muted,
          ),
        ),
        const SizedBox(height: 8),
        const _NotificationsTile(),
        const SizedBox(height: 22),
        const Text(
          'Apariencia',
          style: TextStyle(
            fontWeight: FontWeight.w700,
            fontSize: 13,
            color: AppColors.muted,
          ),
        ),
        const SizedBox(height: 8),
        const _ThemeSelector(),
        const SizedBox(height: 22),
        const Text(
          'Conexión',
          style: TextStyle(
            fontWeight: FontWeight.w700,
            fontSize: 13,
            color: AppColors.muted,
          ),
        ),
        const SizedBox(height: 8),
        Card(
          child: Column(
            children: [
              const _SettingsRow(
                icon: Icons.dns_outlined,
                label: 'Servidor',
                value: AppConfig.odooServer,
              ),
              const Divider(height: 1),
              const _SettingsRow(
                icon: Icons.storage_outlined,
                label: 'Base de datos',
                value: AppConfig.odooDb,
              ),
            ],
          ),
        ),
        const SizedBox(height: 22),
        const Text(
          'Aplicación',
          style: TextStyle(
            fontWeight: FontWeight.w700,
            fontSize: 13,
            color: AppColors.muted,
          ),
        ),
        const SizedBox(height: 8),
        const Card(
          child: _SettingsRow(
            icon: Icons.info_outline,
            label: 'Versión',
            value: '1.0.0',
          ),
        ),
        const SizedBox(height: 28),
        OutlinedButton.icon(
          onPressed: () => _logout(context),
          style: OutlinedButton.styleFrom(
            foregroundColor: AppColors.danger,
            side: const BorderSide(color: AppColors.danger),
          ),
          icon: const Icon(Icons.logout, size: 18),
          label: const Text('Cerrar sesión'),
        ),
      ],
    );
  }
}

class _SettingsRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  const _SettingsRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(icon, color: AppColors.navy),
      title: Text(
        label,
        style: const TextStyle(fontSize: 13, color: AppColors.mutedLight),
      ),
      subtitle: Text(
        value,
        style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
      ),
    );
  }
}

/// Selector de tema (sistema / claro / oscuro) con la preferencia
/// persistida en el dispositivo.
class _ThemeSelector extends StatelessWidget {
  const _ThemeSelector();

  @override
  Widget build(BuildContext context) {
    final ctrl = context.watch<ThemeController>();
    final p = AppColors.of(context);
    const options = [
      (ThemeMode.system, 'Sistema', Icons.brightness_auto_outlined),
      (ThemeMode.light, 'Claro', Icons.light_mode_outlined),
      (ThemeMode.dark, 'Oscuro', Icons.dark_mode_outlined),
    ];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpace.md),
        child: Row(
          children: options.map((o) {
            final selected = ctrl.mode == o.$1;
            return Expanded(
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: () => ctrl.setMode(o.$1),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 180),
                  margin: const EdgeInsets.symmetric(horizontal: 3),
                  padding: const EdgeInsets.symmetric(vertical: AppSpace.md),
                  decoration: BoxDecoration(
                    color: selected ? p.navy : p.surfaceAlt,
                    borderRadius: BorderRadius.circular(AppRadius.md),
                  ),
                  child: Column(
                    children: [
                      Icon(
                        o.$3,
                        size: 20,
                        color: selected
                            ? (p.isDark ? p.navyDeep : Colors.white)
                            : p.muted,
                      ),
                      const SizedBox(height: 5),
                      Text(
                        o.$2,
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: selected
                              ? (p.isDark ? p.navyDeep : Colors.white)
                              : p.muted,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            );
          }).toList(),
        ),
      ),
    );
  }
}

/// Interruptor de las notificaciones de citas en el teléfono. Pide el
/// permiso del sistema la primera vez que se activa.
class _NotificationsTile extends StatefulWidget {
  const _NotificationsTile();

  @override
  State<_NotificationsTile> createState() => _NotificationsTileState();
}

class _NotificationsTileState extends State<_NotificationsTile> {
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
              'Activa las notificaciones para Inmobi en los ajustes del teléfono.',
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
    final p = AppColors.of(context);
    return Card(
      child: Column(
        children: [
          SwitchListTile.adaptive(
            secondary: Icon(Icons.notifications_active_outlined, color: p.navy),
            title: const Text('Avisos de citas'),
            subtitle: Text(
              _enabled
                  ? (_pending > 0
                        ? '$_pending cita${_pending == 1 ? '' : 's'} con aviso programado'
                        : 'Se programan al abrir la Agenda')
                  : 'Desactivado',
              style: AppType.caption.copyWith(color: p.muted),
            ),
            value: _enabled,
            onChanged: _toggle,
          ),
        ],
      ),
    );
  }
}
