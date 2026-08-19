import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/config.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/states.dart';
import '../auth/auth_service.dart';
import '../auth/login_screen.dart';

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
