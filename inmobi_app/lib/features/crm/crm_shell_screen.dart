import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../contacts/contact_list_screen.dart';
import 'lead_funnel_screen.dart';
import 'lead_list_screen.dart';

/// Contenedor del CRM con dos vistas conmutables arriba: las oportunidades
/// (en lista o en embudo) y el directorio de contactos. Es el mismo módulo
/// del ERP, donde leads y contactos conviven.
class CrmShellScreen extends StatefulWidget {
  const CrmShellScreen({super.key});

  @override
  State<CrmShellScreen> createState() => _CrmShellScreenState();
}

class _CrmShellScreenState extends State<CrmShellScreen> {
  int _tab = 0; // 0 = oportunidades, 1 = contactos
  bool _funnelView = false;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
          child: Row(
            children: [
              Expanded(
                child: _SegmentedToggle(
                  options: const ['Oportunidades', 'Contactos'],
                  selectedIndex: _tab,
                  onChanged: (i) => setState(() => _tab = i),
                ),
              ),
              // El conmutador lista/embudo solo aplica a oportunidades.
              if (_tab == 0) ...[
                const SizedBox(width: 10),
                _ViewModeButton(
                  icon: _funnelView
                      ? Icons.view_list_outlined
                      : Icons.view_kanban_outlined,
                  tooltip: _funnelView ? 'Ver como lista' : 'Ver como embudo',
                  onTap: () => setState(() => _funnelView = !_funnelView),
                ),
              ],
            ],
          ),
        ),
        Expanded(
          child: IndexedStack(
            index: _tab,
            children: [
              _funnelView ? const LeadFunnelScreen() : const LeadListScreen(),
              const ContactListScreen(),
            ],
          ),
        ),
      ],
    );
  }
}

/// Conmutador de dos segmentos, con la pastilla deslizándose al cambiar.
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
    return Container(
      height: 40,
      padding: const EdgeInsets.all(3),
      decoration: BoxDecoration(
        color: AppColors.neutralBg,
        borderRadius: BorderRadius.circular(12),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final segmentWidth = constraints.maxWidth / options.length;
          return Stack(
            children: [
              AnimatedPositioned(
                duration: const Duration(milliseconds: 220),
                curve: Curves.easeOutCubic,
                left: segmentWidth * selectedIndex,
                top: 0,
                bottom: 0,
                width: segmentWidth,
                child: Container(
                  decoration: BoxDecoration(
                    color: AppColors.navy,
                    borderRadius: BorderRadius.circular(9),
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
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            color: selected ? Colors.white : AppColors.muted,
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
  final VoidCallback onTap;

  const _ViewModeButton({
    required this.icon,
    required this.tooltip,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Container(
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            color: AppColors.neutralBg,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(icon, size: 20, color: AppColors.navy),
        ),
      ),
    );
  }
}
