import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/choice_chip_row.dart';
import '../../core/widgets/states.dart';
import '../../core/widgets/skeleton.dart';
import '../auth/auth_service.dart';
import 'property_card.dart';
import 'property_form_screen.dart';
import 'property_model.dart';
import 'property_service.dart';

class PropertyListScreen extends StatefulWidget {
  const PropertyListScreen({super.key});

  @override
  State<PropertyListScreen> createState() => _PropertyListScreenState();
}

class _PropertyListScreenState extends State<PropertyListScreen> {
  late final PropertyService _service;
  final _searchCtrl = TextEditingController();
  List<String>? _stateFilter;
  String? _offerFilter;

  List<Property> _properties = [];
  bool _loading = true;
  String? _error;

  static const _stateFilters = [
    (null, 'Todas'),
    (['available'], 'Disponibles'),
    (['reserved'], 'Reservadas'),
    (['sold', 'rented'], 'Vendidas/Arrendadas'),
  ];

  static const _offerFilters = [
    (null, 'Venta y arriendo'),
    ('sale', 'Solo venta'),
    ('rent', 'Solo arriendo'),
  ];

  @override
  void initState() {
    super.initState();
    _service = PropertyService(context.read<AuthService>().odoo);
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final result = await _service.list(
        searchText: _searchCtrl.text,
        states: _stateFilter,
        offerType: _offerFilter,
      );
      setState(() => _properties = result);
    } catch (e) {
      setState(() => _error = 'No se pudieron cargar las propiedades.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _openCreate() async {
    final saved = await Navigator.of(
      context,
    ).push<bool>(MaterialPageRoute(builder: (_) => const PropertyFormScreen()));
    if (saved == true) _load();
  }

  @override
  Widget build(BuildContext context) {
    final currency = NumberFormat.currency(
      locale: 'es_EC',
      symbol: '\$',
      decimalDigits: 0,
    );

    return Scaffold(
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _openCreate,
        icon: const Icon(Icons.add),
        label: const Text('Propiedad'),
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
            child: TextField(
              controller: _searchCtrl,
              decoration: InputDecoration(
                hintText: 'Buscar por título, ciudad o sector...',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: IconButton(
                  icon: const Icon(Icons.close),
                  onPressed: () {
                    _searchCtrl.clear();
                    _load();
                  },
                ),
              ),
              onSubmitted: (_) => _load(),
            ),
          ),
          SizedBox(
            height: 44,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
              itemCount: _stateFilters.length,
              separatorBuilder: (_, _) => const SizedBox(width: 8),
              itemBuilder: (context, i) {
                final (value, label) = _stateFilters[i];
                final selected = _stateFilter == value;
                return ChoiceChip(
                  label: Text(label),
                  selected: selected,
                  selectedColor: AppColors.navy,
                  labelStyle: TextStyle(
                    color: selected ? Colors.white : AppColors.ink,
                    fontWeight: FontWeight.w600,
                    fontSize: 12.5,
                  ),
                  side: BorderSide.none,
                  showCheckmark: false,
                  onSelected: (_) {
                    setState(() => _stateFilter = value);
                    _load();
                  },
                );
              },
            ),
          ),
          ChoiceChipRow(
            options: _offerFilters,
            value: _offerFilter,
            onChanged: (v) {
              setState(() => _offerFilter = v);
              _load();
            },
          ),
          const SizedBox(height: 8),
          Expanded(
            child: RefreshIndicator(
              onRefresh: _load,
              child: _buildBody(currency),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBody(NumberFormat currency) {
    if (_loading) return const SkeletonList();
    if (_error != null) {
      return MessageView(
        icon: Icons.error_outline,
        message: _error!,
        onRetry: _load,
      );
    }
    if (_properties.isEmpty) {
      return const MessageView(
        icon: Icons.home_work_outlined,
        message: 'No se encontraron propiedades.',
      );
    }
    return ListView.separated(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
      itemCount: _properties.length,
      separatorBuilder: (_, _) => const SizedBox(height: 14),
      itemBuilder: (context, i) {
        return PropertyCard(
          property: _properties[i],
          odoo: _service.odoo,
          currency: currency,
        );
      },
    );
  }
}
