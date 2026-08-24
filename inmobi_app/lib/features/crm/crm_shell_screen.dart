import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../contacts/contact_list_screen.dart';
import 'lead_funnel_screen.dart';
import 'lead_list_screen.dart';

/// Contenedor del CRM con tres vistas ejecutivas:
/// 1. Embudo Comercial de Ventas
/// 2. Embudo de Postventa & Seguimiento
/// 3. Directorio de Contactos
class CrmShellScreen extends StatefulWidget {
  const CrmShellScreen({super.key});

  @override
  State<CrmShellScreen> createState() => _CrmShellScreenState();
}

class _CrmShellScreenState extends State<CrmShellScreen> {
  int _tab = 0; // 0 = Ventas, 1 = Postventa, 2 = Contactos
  bool _funnelView = true;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 10),
          child: Row(
            children: [
              Expanded(
                child: _SegmentedToggle(
                  options: const ['Ventas', 'Postventa', 'Contactos'],
                  selectedIndex: _tab,
                  onChanged: (i) {
                    HapticFeedback.selectionClick();
                    setState(() => _tab = i);
                  },
                ),
              ),
              // Conmutador lista / embudo (aplica a Ventas y Postventa)
              if (_tab == 0 || _tab == 1) ...[
                const SizedBox(width: 8),
                _ViewModeButton(
                  icon: _funnelView
                      ? Icons.view_list_rounded
                      : Icons.view_kanban_rounded,
                  tooltip: _funnelView ? 'Ver en listado' : 'Ver en embudo kanban',
                  isDark: isDark,
                  onTap: () {
                    HapticFeedback.lightImpact();
                    setState(() => _funnelView = !_funnelView);
                  },
                ),
              ],
            ],
          ),
        ),
        Expanded(
          child: IndexedStack(
            index: _tab,
            children: [
              // Pestaña 0: Ventas
              _funnelView
                  ? const LeadFunnelScreen(isPostSale: false)
                  : const LeadListScreen(isPostSale: false),
              // Pestaña 1: Postventa
              _funnelView
                  ? const LeadFunnelScreen(isPostSale: true)
                  : const LeadListScreen(isPostSale: true),
              // Pestaña 2: Contactos
              const ContactListScreen(),
            ],
          ),
        ),
      ],
    );
  }
}

/// Selector segmentado moderno de 3 pastillas con animación suave y paleta Inmobi
class _SegmentedToggle extends StatelessWidget {
  final List<String> options;
  final int selectedIndex;
  final ValueChanged<int> onChanged;

  const _SegmentedToggle({
    required this.options,
    required this.selectedIndex,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Container(
      height: 42,
      padding: const EdgeInsets.all(3),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF161330) : const Color(0xFFEBEBF2),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: isDark ? const Color(0xFF28244E) : const Color(0xFFE2E8F0),
        ),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final segmentWidth = constraints.maxWidth / options.length;
          return Stack(
            children: [
              AnimatedPositioned(
                duration: const Duration(milliseconds: 240),
                curve: Curves.easeOutCubic,
                left: segmentWidth * selectedIndex,
                top: 0,
                bottom: 0,
                width: segmentWidth,
                child: Container(
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFF28235D), Color(0xFF1B1740)],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(11),
                    boxShadow: [
                      BoxShadow(
                        color: const Color(0xFF28235D).withValues(alpha: 0.35),
                        blurRadius: 8,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                ),
              ),
              Row(
                children: List.generate(options.length, (i) {
                  final selected = i == selectedIndex;
                  return Expanded(
                    child: GestureDetector(
                      behavior: HitTestBehavior.opaque,
                      onTap: () => onChanged(i),
                      child: Center(
                        child: AnimatedDefaultTextStyle(
                          duration: const Duration(milliseconds: 180),
                          style: TextStyle(
                            fontSize: 12.5,
                            fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
                            color: selected
                                ? Colors.white
                                : (isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B)),
                          ),
                          child: Text(options[i]),
                        ),
                      ),
                    ),
                  );
                }),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _ViewModeButton extends StatelessWidget {
  final IconData icon;
  final String tooltip;
  final bool isDark;
  final VoidCallback onTap;

  const _ViewModeButton({
    required this.icon,
    required this.tooltip,
    required this.isDark,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: Material(
        color: isDark ? const Color(0xFF161330) : const Color(0xFFEBEBF2),
        borderRadius: BorderRadius.circular(14),
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: onTap,
          child: Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: isDark ? const Color(0xFF28244E) : const Color(0xFFE2E8F0),
              ),
            ),
            child: Icon(
              icon,
              size: 20,
              color: isDark ? const Color(0xFF8B85FF) : const Color(0xFF28235D),
            ),
          ),
        ),
      ),
    );
  }
}
