import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../../core/notifications/notification_service.dart';
import '../../core/theme/app_theme.dart';
import '../auth/auth_service.dart';
import '../auth/login_screen.dart';
import '../contacts/contact_list_screen.dart';
import '../contracts/contract_list_screen.dart';
import '../crm/crm_shell_screen.dart';
import '../dashboard/dashboard_screen.dart';
import '../finance/finance_screens.dart';
import '../offers/offer_screens.dart';
import '../properties/property_form_screen.dart';
import '../properties/property_list_screen.dart';
import '../settings/settings_screen.dart';
import '../visits/visit_list_screen.dart';
import '../visits/visit_service.dart';

/// Contenedor principal con Drawer Ejecutivo Inmobi y Barra de Navegación Moderna.
class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      final odoo = context.read<AuthService>().odoo;
      // 1. Inicializar y solicitar permisos de notificación nativos del sistema (Android 13+ / iOS)
      await NotificationService.instance.init();
      await NotificationService.instance.requestPermission();

      // 2. Sincronizar token FCM con Odoo para notificaciones push en segundo plano
      await NotificationService.instance.syncTokenWithOdoo(
        odoo: odoo,
        userId: odoo.userId ?? 0,
      );

      // 3. Programar alarmas locales de citas futuras del asesor
      unawaited(VisitService.scheduleAllUpcoming(odoo, currentUserId: odoo.userId));
    });
  }

  static const _titles = [
    'Panel Inmobi',
    'Propiedades',
    'CRM & Clientes',
    'Agenda de Citas',
    'Opciones & Ajustes',
  ];

  static const _navItems = [
    (
      icon: Icons.dashboard_outlined,
      activeIcon: Icons.dashboard_rounded,
      label: 'Inicio',
    ),
    (
      icon: Icons.home_work_outlined,
      activeIcon: Icons.home_work_rounded,
      label: 'Propiedades',
    ),
    (
      icon: Icons.people_outline_rounded,
      activeIcon: Icons.people_rounded,
      label: 'CRM',
    ),
    (
      icon: Icons.calendar_today_outlined,
      activeIcon: Icons.calendar_month_rounded,
      label: 'Agenda',
    ),
    (
      icon: Icons.grid_view_rounded,
      activeIcon: Icons.grid_view_sharp,
      label: 'Opciones',
    ),
  ];

  void _goTo(int i) {
    if (_index != i) {
      HapticFeedback.lightImpact();
      setState(() => _index = i);
    }
  }

  void _openDrawer() {
    HapticFeedback.selectionClick();
    _scaffoldKey.currentState?.openDrawer();
  }

  @override
  Widget build(BuildContext context) {
    final screens = [
      DashboardScreen(onNavigate: _goTo),
      const PropertyListScreen(),
      const CrmShellScreen(),
      const VisitListScreen(),
      const SettingsScreen(),
    ];

    final isDark = Theme.of(context).brightness == Brightness.dark;
    final userName = context.watch<AuthService>().userName ?? 'Asesor';

    return Scaffold(
      key: _scaffoldKey,
      extendBody: true,
      drawer: _InmobiExecutiveDrawer(
        currentIndex: _index,
        onNavigate: (index) {
          Navigator.of(context).pop(); // Cierra el drawer
          _goTo(index);
        },
      ),
      appBar: (_index == 0 || _index == 3)
          ? null // El dashboard y la agenda tienen sus propios encabezados avanzados
          : AppBar(
              backgroundColor: isDark ? const Color(0xFF161330) : Colors.white,
              surfaceTintColor: Colors.transparent,
              elevation: 0,
              leading: IconButton(
                icon: Container(
                  padding: const EdgeInsets.all(7),
                  decoration: BoxDecoration(
                    color: AppColors.navy.withValues(alpha: isDark ? 0.2 : 0.07),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(
                    Icons.menu_rounded,
                    size: 20,
                    color: AppColors.navy,
                  ),
                ),
                onPressed: _openDrawer,
                tooltip: 'Menú de opciones',
              ),
              title: Text(
                _titles[_index],
                style: const TextStyle(
                  fontWeight: FontWeight.w800,
                  fontSize: 19,
                  letterSpacing: -0.3,
                ),
              ),
              centerTitle: false,
              actions: [
                GestureDetector(
                  onTap: _openDrawer,
                  child: Padding(
                    padding: const EdgeInsets.only(right: 16),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                      decoration: BoxDecoration(
                        color: AppColors.navy.withValues(alpha: isDark ? 0.25 : 0.08),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(
                          color: AppColors.navy.withValues(alpha: 0.15),
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          CircleAvatar(
                            radius: 12,
                            backgroundColor: AppColors.navy,
                            child: Text(
                              userName.isNotEmpty ? userName[0].toUpperCase() : 'A',
                              style: const TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w800,
                                color: Colors.white,
                              ),
                            ),
                          ),
                          const SizedBox(width: 6),
                          Text(
                            userName.split(' ').first,
                            style: const TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                              color: AppColors.navy,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ),
      body: IndexedStack(index: _index, children: screens),
      bottomNavigationBar: _CleanBottomNavBar(
        currentIndex: _index,
        onTap: _goTo,
        items: _navItems,
        isDark: isDark,
      ),
    );
  }
}

/// Menú lateral ejecutivo con branding Inmobi, atajos directos a módulos y perfil
class _InmobiExecutiveDrawer extends StatelessWidget {
  final int currentIndex;
  final ValueChanged<int> onNavigate;

  const _InmobiExecutiveDrawer({
    required this.currentIndex,
    required this.onNavigate,
  });

  Future<void> _logout(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Cerrar sesión'),
        content: const Text('¿Deseas salir del Portal de Inmobi?'),
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
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final auth = context.watch<AuthService>();
    final userName = auth.userName ?? 'Asesor Inmobi';

    return Drawer(
      backgroundColor: isDark ? const Color(0xFF0F0C24) : Colors.white,
      child: SafeArea(
        bottom: false,
        child: Column(
          children: [
            // ── Cabecera Corporativa Inmobi ──
            Container(
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 20),
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    Color(0xFF28235D),
                    Color(0xFF18143C),
                  ],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: [
                          Container(
                            width: 44,
                            height: 44,
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: Colors.white.withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(14),
                              border: Border.all(
                                color: Colors.white.withValues(alpha: 0.2),
                              ),
                            ),
                            child: Image.asset(
                              'assets/branding/logo_white.png',
                              fit: BoxFit.contain,
                            ),
                          ),
                          const SizedBox(width: 12),
                          const Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'INMOBI',
                                style: TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.w900,
                                  letterSpacing: 2,
                                  color: Colors.white,
                                ),
                              ),
                              Text(
                                'Inmobi Ecuador',
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w600,
                                  color: Colors.white70,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: const Color(0xFFD81F26),
                          borderRadius: BorderRadius.circular(100),
                        ),
                        child: const Text(
                          'OFICIAL',
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w900,
                            color: Colors.white,
                            letterSpacing: 0.8,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  // Tarjeta Asesor
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.09),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
                    ),
                    child: Row(
                      children: [
                        CircleAvatar(
                          radius: 20,
                          backgroundColor: const Color(0xFFD81F26),
                          child: Text(
                            userName.isNotEmpty ? userName[0].toUpperCase() : 'A',
                            style: const TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.w800,
                              color: Colors.white,
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                userName,
                                style: const TextStyle(
                                  fontSize: 14.5,
                                  fontWeight: FontWeight.w800,
                                  color: Colors.white,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                              const SizedBox(height: 2),
                              Row(
                                children: [
                                  Container(
                                    width: 7,
                                    height: 7,
                                    decoration: const BoxDecoration(
                                      color: Color(0xFF10B981),
                                      shape: BoxShape.circle,
                                    ),
                                  ),
                                  const SizedBox(width: 5),
                                  const Text(
                                    'Asesor Conectado',
                                    style: TextStyle(
                                      fontSize: 11.5,
                                      color: Colors.white70,
                                      fontWeight: FontWeight.w500,
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
                ],
              ),
            ),

            // ── Lista de Opciones y Módulos ──
            Expanded(
              child: ListView(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
                children: [
                  _DrawerSectionLabel(title: 'NAVEGACIÓN PRINCIPAL'),
                  _DrawerTile(
                    icon: Icons.dashboard_outlined,
                    activeIcon: Icons.dashboard_rounded,
                    title: 'Panel General',
                    isSelected: currentIndex == 0,
                    onTap: () => onNavigate(0),
                  ),
                  _DrawerTile(
                    icon: Icons.home_work_outlined,
                    activeIcon: Icons.home_work_rounded,
                    title: 'Catálogo de Propiedades',
                    isSelected: currentIndex == 1,
                    onTap: () => onNavigate(1),
                  ),
                  _DrawerTile(
                    icon: Icons.people_outline_rounded,
                    activeIcon: Icons.people_rounded,
                    title: 'CRM & Pipeline',
                    isSelected: currentIndex == 2,
                    onTap: () => onNavigate(2),
                  ),
                  _DrawerTile(
                    icon: Icons.calendar_today_outlined,
                    activeIcon: Icons.calendar_month_rounded,
                    title: 'Agenda & Visitas',
                    isSelected: currentIndex == 3,
                    onTap: () => onNavigate(3),
                  ),

                  const SizedBox(height: 12),
                  _DrawerSectionLabel(title: 'GESTIÓN COMERCIAL'),
                  _DrawerActionTile(
                    icon: Icons.contacts_outlined,
                    title: 'Directorio de Contactos',
                    subtitle: 'Propietarios e interesados',
                    color: const Color(0xFF28235D),
                    onTap: () {
                      Navigator.of(context).pop();
                      Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => const ContactListScreen()),
                      );
                    },
                  ),
                  _DrawerActionTile(
                    icon: Icons.description_outlined,
                    title: 'Contratos de Alquiler / Venta',
                    subtitle: 'Expedientes activos y reservas',
                    color: const Color(0xFF3F3787),
                    onTap: () {
                      Navigator.of(context).pop();
                      Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => const ContractListScreen()),
                      );
                    },
                  ),
                  _DrawerActionTile(
                    icon: Icons.handshake_outlined,
                    title: 'Ofertas y Negociaciones',
                    subtitle: 'Propuestas de compra/renta',
                    color: const Color(0xFF0284C7),
                    onTap: () {
                      Navigator.of(context).pop();
                      Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => const OfferListScreen()),
                      );
                    },
                  ),
                  _DrawerActionTile(
                    icon: Icons.payments_outlined,
                    title: 'Mis Comisiones',
                    subtitle: 'Liquidaciones de ventas',
                    color: const Color(0xFF10B981),
                    onTap: () {
                      Navigator.of(context).pop();
                      Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => const CommissionListScreen()),
                      );
                    },
                  ),
                  _DrawerActionTile(
                    icon: Icons.add_home_work_outlined,
                    title: 'Registrar Nueva Propiedad',
                    subtitle: 'Captación en Inmobi',
                    color: const Color(0xFFD81F26),
                    onTap: () {
                      Navigator.of(context).pop();
                      Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => const PropertyFormScreen()),
                      );
                    },
                  ),

                  const SizedBox(height: 12),
                  _DrawerSectionLabel(title: 'PREFERENCIAS'),
                  _DrawerTile(
                    icon: Icons.tune_rounded,
                    activeIcon: Icons.tune_rounded,
                    title: 'Configuración & Sistema',
                    isSelected: currentIndex == 4,
                    onTap: () => onNavigate(4),
                  ),
                ],
              ),
            ),

            // ── Pie del Drawer con Cerrar Sesión ──
            Container(
              padding: const EdgeInsets.fromLTRB(16, 10, 16, 20),
              decoration: BoxDecoration(
                color: isDark ? const Color(0xFF161330) : const Color(0xFFF8FAFC),
                border: Border(
                  top: BorderSide(
                    color: isDark ? const Color(0xFF28244E) : const Color(0xFFE2E8F0),
                  ),
                ),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => _logout(context),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: const Color(0xFFD81F26),
                        side: const BorderSide(color: Color(0xFFD81F26), width: 1.2),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(14),
                        ),
                        padding: const EdgeInsets.symmetric(vertical: 12),
                      ),
                      icon: const Icon(Icons.logout_rounded, size: 18),
                      label: const Text(
                        'Cerrar Sesión',
                        style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _DrawerSectionLabel extends StatelessWidget {
  final String title;
  const _DrawerSectionLabel({required this.title});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 10, top: 8, bottom: 6),
      child: Text(
        title,
        style: const TextStyle(
          fontSize: 10.5,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.9,
          color: Color(0xFF94A3B8),
        ),
      ),
    );
  }
}

class _DrawerTile extends StatelessWidget {
  final IconData icon;
  final IconData activeIcon;
  final String title;
  final bool isSelected;
  final VoidCallback onTap;

  const _DrawerTile({
    required this.icon,
    required this.activeIcon,
    required this.title,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Material(
        color: isSelected
            ? (isDark
                ? const Color(0xFF28235D).withValues(alpha: 0.35)
                : const Color(0xFF28235D).withValues(alpha: 0.08))
            : Colors.transparent,
        borderRadius: BorderRadius.circular(14),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(14),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
            child: Row(
              children: [
                Icon(
                  isSelected ? activeIcon : icon,
                  size: 21,
                  color: isSelected
                      ? (isDark ? const Color(0xFF8B85FF) : const Color(0xFF28235D))
                      : const Color(0xFF64748B),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Text(
                    title,
                    style: TextStyle(
                      fontSize: 13.5,
                      fontWeight: isSelected ? FontWeight.w800 : FontWeight.w600,
                      color: isSelected
                          ? (isDark ? Colors.white : const Color(0xFF28235D))
                          : (isDark ? const Color(0xFFCBD5E1) : const Color(0xFF334155)),
                    ),
                  ),
                ),
                if (isSelected)
                  Container(
                    width: 6,
                    height: 6,
                    decoration: const BoxDecoration(
                      color: Color(0xFFD81F26),
                      shape: BoxShape.circle,
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _DrawerActionTile extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final Color color;
  final VoidCallback onTap;

  const _DrawerActionTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(14),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: isDark ? 0.22 : 0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(icon, size: 18, color: isDark ? const Color(0xFF8B85FF) : color),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                          color: isDark ? Colors.white : const Color(0xFF0F172A),
                        ),
                      ),
                      Text(
                        subtitle,
                        style: const TextStyle(
                          fontSize: 11,
                          color: Color(0xFF94A3B8),
                        ),
                      ),
                    ],
                  ),
                ),
                const Icon(
                  Icons.chevron_right_rounded,
                  size: 18,
                  color: Color(0xFF94A3B8),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Barra de navegación ejecutiva y moderna con resaltado sutil tipo pill
class _CleanBottomNavBar extends StatelessWidget {
  final int currentIndex;
  final ValueChanged<int> onTap;
  final List<({IconData icon, IconData activeIcon, String label})> items;
  final bool isDark;

  const _CleanBottomNavBar({
    required this.currentIndex,
    required this.onTap,
    required this.items,
    required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF14112E) : Colors.white,
        border: Border(
          top: BorderSide(
            color: isDark ? const Color(0xFF28244E) : const Color(0xFFE5E7EB),
            width: 1,
          ),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: isDark ? 0.35 : 0.05),
            blurRadius: 16,
            offset: const Offset(0, -4),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 64,
          child: Row(
            children: List.generate(items.length, (i) {
              final item = items[i];
              final selected = i == currentIndex;

              return Expanded(
                child: InkWell(
                  onTap: () {
                    HapticFeedback.selectionClick();
                    onTap(i);
                  },
                  splashColor: Colors.transparent,
                  highlightColor: Colors.transparent,
                  child: Center(
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 200),
                      curve: Curves.easeInOut,
                      padding: EdgeInsets.symmetric(
                        horizontal: selected ? 12 : 6,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: selected
                            ? (isDark
                                ? const Color(0xFF28235D).withValues(alpha: 0.5)
                                : const Color(0xFF28235D).withValues(alpha: 0.08))
                            : Colors.transparent,
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            selected ? item.activeIcon : item.icon,
                            size: 22,
                            color: selected
                                ? (isDark
                                    ? const Color(0xFF9E99FF)
                                    : const Color(0xFF28235D))
                                : (isDark
                                    ? const Color(0xFF64748B)
                                    : const Color(0xFF94A3B8)),
                          ),
                          const SizedBox(height: 3),
                          Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                item.label,
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: selected
                                      ? FontWeight.w800
                                      : FontWeight.w500,
                                  color: selected
                                      ? (isDark
                                          ? Colors.white
                                          : const Color(0xFF28235D))
                                      : (isDark
                                          ? const Color(0xFF64748B)
                                          : const Color(0xFF94A3B8)),
                                ),
                              ),
                              if (selected) ...[
                                const SizedBox(width: 3),
                                Container(
                                  width: 4,
                                  height: 4,
                                  decoration: const BoxDecoration(
                                    color: Color(0xFFD81F26),
                                    shape: BoxShape.circle,
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              );
            }),
          ),
        ),
      ),
    );
  }
}
