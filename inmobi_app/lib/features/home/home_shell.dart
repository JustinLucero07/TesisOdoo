import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart' show ScrollDirection;
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../../core/notifications/notification_service.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/glass.dart';
import '../../core/widgets/glass_nav_bar.dart';
import '../../core/widgets/odoo_image.dart';
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

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();

  final ValueNotifier<bool> _navCollapsed = ValueNotifier(false);

  bool _handleScroll(ScrollNotification n) {
    if (n.metrics.axis != Axis.vertical) return false;

    if (n is UserScrollNotification) {
      switch (n.direction) {
        case ScrollDirection.reverse:
          _navCollapsed.value = true;
        case ScrollDirection.forward:
          _navCollapsed.value = false;
        case ScrollDirection.idle:
          break;
      }
    }

    if (n.metrics.pixels <= n.metrics.minScrollExtent + 4) {
      _navCollapsed.value = false;
    }
    return false;
  }

  @override
  void dispose() {
    _navCollapsed.dispose();
    super.dispose();
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      final odoo = context.read<AuthService>().odoo;

      await NotificationService.instance.init();
      await NotificationService.instance.requestPermission();

      await NotificationService.instance.syncTokenWithOdoo(
        odoo: odoo,
        userId: odoo.userId ?? 0,
      );

      unawaited(
        VisitService.scheduleAllUpcoming(odoo, currentUserId: odoo.userId),
      );
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
    GlassNavItem(
      icon: Icons.dashboard_outlined,
      activeIcon: Icons.dashboard_rounded,
      label: 'Inicio',
    ),
    GlassNavItem(
      icon: Icons.home_work_outlined,
      activeIcon: Icons.home_work_rounded,
      label: 'Propiedades',
    ),
    GlassNavItem(
      icon: Icons.people_outline_rounded,
      activeIcon: Icons.people_rounded,
      label: 'CRM',
    ),
    GlassNavItem(
      icon: Icons.calendar_today_outlined,
      activeIcon: Icons.calendar_month_rounded,
      label: 'Agenda',
    ),
    GlassNavItem(
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
    final colors = AppColors.of(context);
    final auth = context.watch<AuthService>();
    final userName = auth.userName ?? 'Asesor';

    return Scaffold(
      key: _scaffoldKey,

      extendBody: true,
      extendBodyBehindAppBar: true,
      drawer: _InmobiExecutiveDrawer(
        currentIndex: _index,
        onNavigate: (index) {
          Navigator.of(context).pop();
          _goTo(index);
        },
      ),
      appBar: (_index == 0 || _index == 3)
          ? null
          : AppBar(
              backgroundColor: Colors.transparent,
              surfaceTintColor: Colors.transparent,
              flexibleSpace: const GlassBar(),
              elevation: 0,
              leading: IconButton(
                icon: Container(
                  padding: const EdgeInsets.all(7),
                  decoration: BoxDecoration(
                    color: colors.navy.withValues(alpha: isDark ? 0.2 : 0.07),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(Icons.menu_rounded, size: 20, color: colors.navy),
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
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 5,
                      ),
                      decoration: BoxDecoration(
                        color: colors.navy.withValues(
                          alpha: isDark ? 0.25 : 0.08,
                        ),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(
                          color: colors.navy.withValues(alpha: 0.15),
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          UserAvatar(
                            odoo: auth.odoo,
                            userId: auth.odoo.userId ?? 0,
                            userName: userName,
                            radius: 12,
                            backgroundColor: colors.navy,
                          ),
                          const SizedBox(width: 6),
                          Text(
                            userName.split(' ').first,
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                              color: colors.navy,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ),
      body: NotificationListener<ScrollNotification>(
        onNotification: _handleScroll,
        child: IndexedStack(index: _index, children: screens),
      ),
      bottomNavigationBar: GlassNavBar(
        currentIndex: _index,
        onTap: _goTo,
        items: _navItems,
        collapsed: _navCollapsed,
      ),
    );
  }
}

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
            style: FilledButton.styleFrom(
              backgroundColor: const Color(0xFFD81F26),
            ),
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
            Container(
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 20),
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  colors: [Color(0xFF28235D), Color(0xFF18143C)],
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
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 4,
                        ),
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

                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.09),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(
                        color: Colors.white.withValues(alpha: 0.12),
                      ),
                    ),
                    child: Row(
                      children: [
                        UserAvatar(
                          odoo: auth.odoo,
                          userId: auth.odoo.userId ?? 0,
                          userName: userName,
                          radius: 20,
                          backgroundColor: const Color(0xFFD81F26),
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

            Expanded(
              child: ListView(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 14,
                ),
                children: [
                  // Este menú solo lleva lo que NO está en la barra inferior:
                  // duplicar ahí las 5 secciones principales dejaba dos
                  // navegaciones compitiendo por los mismos destinos.
                  _DrawerSectionLabel(title: 'GESTIÓN COMERCIAL'),
                  _DrawerActionTile(
                    icon: Icons.contacts_outlined,
                    title: 'Directorio de Contactos',
                    subtitle: 'Propietarios e interesados',
                    color: const Color(0xFF28235D),
                    onTap: () {
                      Navigator.of(context).pop();
                      Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => const ContactListScreen(),
                        ),
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
                        MaterialPageRoute(
                          builder: (_) => const ContractListScreen(),
                        ),
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
                        MaterialPageRoute(
                          builder: (_) => const OfferListScreen(),
                        ),
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
                        MaterialPageRoute(
                          builder: (_) => const CommissionListScreen(),
                        ),
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
                        MaterialPageRoute(
                          builder: (_) => const PropertyFormScreen(),
                        ),
                      );
                    },
                  ),
                ],
              ),
            ),

            Container(
              padding: const EdgeInsets.fromLTRB(16, 10, 16, 20),
              decoration: BoxDecoration(
                color: isDark
                    ? const Color(0xFF161330)
                    : const Color(0xFFF8FAFC),
                border: Border(
                  top: BorderSide(
                    color: isDark
                        ? const Color(0xFF28244E)
                        : const Color(0xFFE2E8F0),
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
                        side: const BorderSide(
                          color: Color(0xFFD81F26),
                          width: 1.2,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(14),
                        ),
                        padding: const EdgeInsets.symmetric(vertical: 12),
                      ),
                      icon: const Icon(Icons.logout_rounded, size: 18),
                      label: const Text(
                        'Cerrar Sesión',
                        style: TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 13,
                        ),
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
        style: TextStyle(
          fontSize: 10.5,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.9,
          color: AppColors.of(context).mutedLight,
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
    final colors = AppColors.of(context);

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
                  child: Icon(
                    icon,
                    size: 18,
                    color: isDark ? const Color(0xFF8B85FF) : color,
                  ),
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
                          color: colors.ink,
                        ),
                      ),
                      Text(
                        subtitle,
                        style: TextStyle(
                          fontSize: 11,
                          color: colors.mutedLight,
                        ),
                      ),
                    ],
                  ),
                ),
                Icon(
                  Icons.chevron_right_rounded,
                  size: 18,
                  color: colors.mutedLight,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
