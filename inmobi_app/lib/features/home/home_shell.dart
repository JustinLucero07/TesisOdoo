import 'package:flutter/material.dart';

import '../crm/lead_list_screen.dart';
import '../dashboard/dashboard_screen.dart';
import '../properties/property_list_screen.dart';
import '../settings/settings_screen.dart';
import '../visits/visit_list_screen.dart';

/// Contenedor con navegación inferior de 5 secciones: Inicio (dashboard con
/// KPIs reales), Propiedades, CRM, Agenda y Configuración.
class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;

  static const _titles = [
    'Inicio',
    'Propiedades',
    'CRM',
    'Agenda',
    'Configuración',
  ];

  void _goTo(int i) => setState(() => _index = i);

  @override
  Widget build(BuildContext context) {
    final screens = [
      DashboardScreen(onNavigate: _goTo),
      const PropertyListScreen(),
      const LeadListScreen(),
      const VisitListScreen(),
      const SettingsScreen(),
    ];

    return Scaffold(
      appBar: AppBar(title: Text(_titles[_index])),
      body: IndexedStack(index: _index, children: screens),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _index,
        onTap: _goTo,
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.dashboard_outlined),
            activeIcon: Icon(Icons.dashboard),
            label: 'Inicio',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.home_work_outlined),
            activeIcon: Icon(Icons.home_work),
            label: 'Propiedades',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.people_outline),
            activeIcon: Icon(Icons.people),
            label: 'CRM',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.calendar_today_outlined),
            activeIcon: Icon(Icons.calendar_today),
            label: 'Agenda',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.settings_outlined),
            activeIcon: Icon(Icons.settings),
            label: 'Configuración',
          ),
        ],
      ),
    );
  }
}
