import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// Estado de carga centrado y consistente para cualquier pantalla.
class LoadingView extends StatelessWidget {
  const LoadingView({super.key});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: CircularProgressIndicator(color: AppColors.of(context).navy),
    );
  }
}

/// Estado vacío/error con ícono + mensaje + acción opcional de reintentar.
class MessageView extends StatelessWidget {
  final IconData icon;
  final String message;
  final VoidCallback? onRetry;

  const MessageView({
    super.key,
    required this.icon,
    required this.message,
    this.onRetry,
  });

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 44, color: colors.mutedLight),
            const SizedBox(height: 14),
            Text(
              message,
              textAlign: TextAlign.center,
              style: TextStyle(color: colors.muted, fontSize: 14),
            ),
            if (onRetry != null) ...[
              const SizedBox(height: 14),
              OutlinedButton(
                onPressed: onRetry,
                child: const Text('Reintentar'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Círculo con inicial(es) — usado como avatar cuando no hay foto.
class InitialsAvatar extends StatelessWidget {
  final String text;
  final double size;
  final Color? color;

  const InitialsAvatar({
    super.key,
    required this.text,
    this.size = 44,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final resolvedColor = color ?? AppColors.of(context).navy;
    final initials = text.trim().isEmpty
        ? '?'
        : text
              .trim()
              .split(RegExp(r'\s+'))
              .take(2)
              .map((w) => w[0].toUpperCase())
              .join();
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: resolvedColor.withValues(alpha: 0.12),
        shape: BoxShape.circle,
      ),
      alignment: Alignment.center,
      child: Text(
        initials,
        style: TextStyle(
          color: resolvedColor,
          fontWeight: FontWeight.w700,
          fontSize: size * 0.36,
        ),
      ),
    );
  }
}
