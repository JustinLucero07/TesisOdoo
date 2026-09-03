import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/glass.dart';
import '../../core/widgets/glass_nav_bar.dart';
import '../../core/widgets/motion.dart';
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

  double? _minPrice;
  double? _maxPrice;
  double? _minArea;
  double? _maxArea;
  int? _bedrooms;
  double? _bathrooms;
  int? _parkingSpaces;
  String? _sector;
  bool _onlyExclusive = false;
  String _sortOrder = 'create_date desc';

  List<Property> _properties = [];
  bool _loading = true;
  String? _error;

  int _quickFilterIndex = 0;

  static const _quickFilters = [
    (states: <String>[], offer: null, label: 'Todas'),
    (states: ['available'], offer: null, label: 'Disponibles'),
    (states: <String>[], offer: 'sale', label: 'En Venta'),
    (states: <String>[], offer: 'rent', label: 'En Arriendo'),
    (states: ['reserved'], offer: null, label: 'Reservadas'),
    (states: ['sold', 'rented'], offer: null, label: 'Cerradas'),
  ];

  int get _activeAdvancedFilterCount {
    int count = 0;
    if (_minPrice != null && _minPrice! > 0) count++;
    if (_maxPrice != null && _maxPrice! > 0) count++;
    if (_minArea != null && _minArea! > 0) count++;
    if (_maxArea != null && _maxArea! > 0) count++;
    if (_bedrooms != null) count++;
    if (_bathrooms != null) count++;
    if (_parkingSpaces != null) count++;
    if (_sector != null && _sector!.isNotEmpty) count++;
    if (_onlyExclusive) count++;
    if (_sortOrder != 'create_date desc') count++;
    return count;
  }

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
        minPrice: _minPrice,
        maxPrice: _maxPrice,
        minArea: _minArea,
        maxArea: _maxArea,
        bedrooms: _bedrooms,
        bathrooms: _bathrooms,
        parkingSpaces: _parkingSpaces,
        sector: _sector,
        isExclusive: _onlyExclusive ? true : null,
        order: _sortOrder,
      );
      if (mounted) setState(() => _properties = result);
    } catch (e) {
      if (mounted)
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

  void _openFilterModal() {
    HapticFeedback.lightImpact();
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => _PropertyFilterSheet(
        minPrice: _minPrice,
        maxPrice: _maxPrice,
        minArea: _minArea,
        maxArea: _maxArea,
        bedrooms: _bedrooms,
        bathrooms: _bathrooms,
        parkingSpaces: _parkingSpaces,
        sector: _sector,
        onlyExclusive: _onlyExclusive,
        sortOrder: _sortOrder,
        onApply: (minP, maxP, minA, maxA, bed, bath, park, sec, excl, sort) {
          setState(() {
            _minPrice = minP;
            _maxPrice = maxP;
            _minArea = minA;
            _maxArea = maxA;
            _bedrooms = bed;
            _bathrooms = bath;
            _parkingSpaces = park;
            _sector = sec;
            _onlyExclusive = excl;
            _sortOrder = sort;
          });
          _load();
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final currency = NumberFormat.currency(
      locale: 'es_EC',
      symbol: '\$',
      decimalDigits: 0,
    );
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colors = AppColors.of(context);
    final activeFilters = _activeAdvancedFilterCount;

    return Scaffold(
      floatingActionButton: Padding(
        padding: const EdgeInsets.only(bottom: GlassNavBar.reservedHeight),
        child: FloatingActionButton.small(
          heroTag: null,
          onPressed: _openCreate,
          backgroundColor: const Color(0xFFD81F26),
          elevation: 4,
          tooltip: 'Nueva Propiedad',
          child: const Icon(Icons.add_rounded, color: Colors.white, size: 22),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            SliverToBoxAdapter(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: EdgeInsets.fromLTRB(
                      16,
                      MediaQuery.paddingOf(context).top + 12,
                      16,
                      4,
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _searchCtrl,
                            decoration: InputDecoration(
                              hintText: 'Buscar por título, ciudad o sector...',
                              prefixIcon: const Icon(Icons.search_rounded),
                              suffixIcon: _searchCtrl.text.isNotEmpty
                                  ? IconButton(
                                      icon: const Icon(
                                        Icons.close_rounded,
                                        size: 20,
                                      ),
                                      onPressed: () {
                                        _searchCtrl.clear();
                                        _load();
                                      },
                                    )
                                  : null,
                            ),
                            onChanged: (_) {
                              if (_searchCtrl.text.isEmpty) _load();
                            },
                            onSubmitted: (_) => _load(),
                          ),
                        ),
                        const SizedBox(width: 8),

                        Stack(
                          clipBehavior: Clip.none,
                          children: [
                            Material(
                              color: activeFilters > 0
                                  ? (isDark
                                        ? const Color(0xFF28235D)
                                        : const Color(0xFFEBEBF2))
                                  : (isDark
                                        ? const Color(0xFF1E1A3E)
                                        : const Color(0xFFF1F5F9)),
                              borderRadius: BorderRadius.circular(14),
                              child: InkWell(
                                borderRadius: BorderRadius.circular(14),
                                onTap: _openFilterModal,
                                child: Container(
                                  width: 44,
                                  height: 44,
                                  decoration: BoxDecoration(
                                    borderRadius: BorderRadius.circular(14),
                                    border: Border.all(
                                      color: activeFilters > 0
                                          ? const Color(0xFF28235D)
                                          : (isDark
                                                ? Colors.white12
                                                : const Color(0xFFE2E8F0)),
                                    ),
                                  ),
                                  child: Icon(
                                    Icons.tune_rounded,
                                    size: 20,
                                    color: isDark
                                        ? Colors.white
                                        : const Color(0xFF28235D),
                                  ),
                                ),
                              ),
                            ),
                            if (activeFilters > 0)
                              Positioned(
                                top: -4,
                                right: -4,
                                child: Container(
                                  padding: const EdgeInsets.all(4),
                                  decoration: const BoxDecoration(
                                    color: Color(0xFFD81F26),
                                    shape: BoxShape.circle,
                                  ),
                                  constraints: const BoxConstraints(
                                    minWidth: 18,
                                    minHeight: 18,
                                  ),
                                  child: Center(
                                    child: Text(
                                      '$activeFilters',
                                      style: const TextStyle(
                                        color: Colors.white,
                                        fontSize: 10,
                                        fontWeight: FontWeight.w900,
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                          ],
                        ),
                      ],
                    ),
                  ),

                  SizedBox(
                    height: 42,
                    child: ListView.separated(
                      scrollDirection: Axis.horizontal,
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 4,
                      ),
                      itemCount: _quickFilters.length,
                      separatorBuilder: (_, _) => const SizedBox(width: 8),
                      itemBuilder: (context, i) {
                        final filter = _quickFilters[i];
                        final selected = _quickFilterIndex == i;
                        return GestureDetector(
                          onTap: () {
                            HapticFeedback.selectionClick();
                            setState(() {
                              _quickFilterIndex = i;
                              _stateFilter = filter.states.isEmpty
                                  ? null
                                  : filter.states;
                              _offerFilter = filter.offer;
                            });
                            _load();
                          },
                          child: AnimatedContainer(
                            duration: const Duration(milliseconds: 180),
                            padding: const EdgeInsets.symmetric(
                              horizontal: 14,
                              vertical: 6,
                            ),
                            decoration: BoxDecoration(
                              color: selected
                                  ? const Color(0xFF28235D)
                                  : (isDark
                                        ? const Color(0xFF1E1A3E)
                                        : const Color(0xFFF1F5F9)),
                              borderRadius: BorderRadius.circular(20),
                              border: Border.all(
                                color: selected
                                    ? const Color(0xFF28235D)
                                    : (isDark
                                          ? Colors.white12
                                          : const Color(0xFFE2E8F0)),
                              ),
                            ),
                            child: Center(
                              child: Text(
                                filter.label,
                                style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: selected
                                      ? FontWeight.w800
                                      : FontWeight.w600,
                                  color: selected
                                      ? Colors.white
                                      : (isDark ? Colors.white70 : colors.ink),
                                ),
                              ),
                            ),
                          ),
                        );
                      },
                    ),
                  ),

                  if (!_loading && _error == null && _properties.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.fromLTRB(18, 4, 18, 8),
                      child: Row(
                        children: [
                          Text(
                            '${_properties.length} ${_properties.length == 1 ? 'propiedad encontrada' : 'propiedades encontradas'}',
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                              color: isDark
                                  ? const Color(0xFF94A3B8)
                                  : const Color(0xFF64748B),
                            ),
                          ),
                          const Spacer(),
                          if (activeFilters > 0)
                            GestureDetector(
                              onTap: () {
                                setState(() {
                                  _minPrice = null;
                                  _maxPrice = null;
                                  _bedrooms = null;
                                  _bathrooms = null;
                                  _onlyExclusive = false;
                                  _sortOrder = 'create_date desc';
                                });
                                _load();
                              },
                              child: const Text(
                                'Limpiar filtros',
                                style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w700,
                                  color: Color(0xFFD81F26),
                                ),
                              ),
                            ),
                        ],
                      ),
                    ),
                ],
              ),
            ),

            if (_loading)
              const SliverFillRemaining(child: SkeletonList())
            else if (_error != null)
              SliverFillRemaining(
                child: MessageView(
                  icon: Icons.error_outline,
                  message: _error!,
                  onRetry: _load,
                ),
              )
            else if (_properties.isEmpty)
              const SliverFillRemaining(
                child: MessageView(
                  icon: Icons.home_work_outlined,
                  message: 'No se encontraron propiedades.',
                ),
              )
            else
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(16, 4, 16, 110),
                sliver: SliverList(
                  delegate: SliverChildBuilderDelegate(
                    (context, index) {
                      if (index.isOdd) return const SizedBox(height: 14);
                      final propIndex = index ~/ 2;
                      return FadeSlideIn(
                        index: propIndex,
                        child: PropertyCard(
                          property: _properties[propIndex],
                          odoo: context.read<AuthService>().odoo,
                          currency: currency,
                        ),
                      );
                    },
                    childCount: _properties.isEmpty
                        ? 0
                        : (_properties.length * 2 - 1),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _PropertyFilterSheet extends StatefulWidget {
  final double? minPrice;
  final double? maxPrice;
  final double? minArea;
  final double? maxArea;
  final int? bedrooms;
  final double? bathrooms;
  final int? parkingSpaces;
  final String? sector;
  final bool onlyExclusive;
  final String sortOrder;
  final Function(
    double?,
    double?,
    double?,
    double?,
    int?,
    double?,
    int?,
    String?,
    bool,
    String,
  )
  onApply;

  const _PropertyFilterSheet({
    required this.minPrice,
    required this.maxPrice,
    required this.minArea,
    required this.maxArea,
    required this.bedrooms,
    required this.bathrooms,
    required this.parkingSpaces,
    required this.sector,
    required this.onlyExclusive,
    required this.sortOrder,
    required this.onApply,
  });

  @override
  State<_PropertyFilterSheet> createState() => _PropertyFilterSheetState();
}

class _PropertyFilterSheetState extends State<_PropertyFilterSheet> {
  late final TextEditingController _minPriceCtrl;
  late final TextEditingController _maxPriceCtrl;
  late final TextEditingController _minAreaCtrl;
  late final TextEditingController _maxAreaCtrl;
  int? _bedrooms;
  double? _bathrooms;
  int? _parkingSpaces;
  String? _sector;
  bool _onlyExclusive = false;
  String _sortOrder = 'create_date desc';

  static const _cuencaSectors = [
    'Remigio Crespo',
    'Challuabamba',
    'Yanuncay',
    'Totoracocha',
    'Ricaurte',
    'El Vergel',
    'Misicata',
    'San Joaquín',
    'Monay',
    'Baños',
  ];

  @override
  void initState() {
    super.initState();
    _minPriceCtrl = TextEditingController(
      text: widget.minPrice != null ? widget.minPrice!.toInt().toString() : '',
    );
    _maxPriceCtrl = TextEditingController(
      text: widget.maxPrice != null ? widget.maxPrice!.toInt().toString() : '',
    );
    _minAreaCtrl = TextEditingController(
      text: widget.minArea != null ? widget.minArea!.toInt().toString() : '',
    );
    _maxAreaCtrl = TextEditingController(
      text: widget.maxArea != null ? widget.maxArea!.toInt().toString() : '',
    );
    _bedrooms = widget.bedrooms;
    _bathrooms = widget.bathrooms;
    _parkingSpaces = widget.parkingSpaces;
    _sector = widget.sector;
    _onlyExclusive = widget.onlyExclusive;
    _sortOrder = widget.sortOrder;
  }

  @override
  void dispose() {
    _minPriceCtrl.dispose();
    _maxPriceCtrl.dispose();
    _minAreaCtrl.dispose();
    _maxAreaCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colors = AppColors.of(context);

    return GlassSurface(
      level: GlassLevel.thick,
      borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      child: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 10),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: isDark ? Colors.white24 : Colors.grey[300],
                    borderRadius: BorderRadius.circular(10),
                  ),
                ),
              ),
              const SizedBox(height: 16),

              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Filtros Avanzados',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
                  ),
                  TextButton(
                    onPressed: () {
                      setState(() {
                        _minPriceCtrl.clear();
                        _maxPriceCtrl.clear();
                        _minAreaCtrl.clear();
                        _maxAreaCtrl.clear();
                        _bedrooms = null;
                        _bathrooms = null;
                        _parkingSpaces = null;
                        _sector = null;
                        _onlyExclusive = false;
                        _sortOrder = 'create_date desc';
                      });
                    },
                    child: const Text(
                      'Restablecer',
                      style: TextStyle(
                        color: Color(0xFFD81F26),
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ),
              const Divider(height: 20),

              const Text(
                'Ordenar por',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                children: [
                  _FilterChoiceChip(
                    label: 'Más recientes',
                    selected: _sortOrder == 'create_date desc',
                    onTap: () =>
                        setState(() => _sortOrder = 'create_date desc'),
                  ),
                  _FilterChoiceChip(
                    label: 'Menor precio',
                    selected: _sortOrder == 'sale_price asc',
                    onTap: () => setState(() => _sortOrder = 'sale_price asc'),
                  ),
                  _FilterChoiceChip(
                    label: 'Mayor precio',
                    selected: _sortOrder == 'sale_price desc',
                    onTap: () => setState(() => _sortOrder = 'sale_price desc'),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              const Text(
                'Sector / Ubicación',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 8),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    _FilterChoiceChip(
                      label: 'Cualquier sector',
                      selected: _sector == null,
                      onTap: () => setState(() => _sector = null),
                    ),
                    const SizedBox(width: 8),
                    ..._cuencaSectors.map((sec) {
                      return Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: _FilterChoiceChip(
                          label: sec,
                          selected: _sector == sec,
                          onTap: () => setState(() => _sector = sec),
                        ),
                      );
                    }),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              const Text(
                'Rango de Precio (\$ USD)',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _minPriceCtrl,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        hintText: 'Mínimo',
                        prefixText: '\$ ',
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextField(
                      controller: _maxPriceCtrl,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        hintText: 'Máximo',
                        prefixText: '\$ ',
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              const Text(
                'Área / Superficie (m²)',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _minAreaCtrl,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        hintText: 'Área mín. m²',
                        suffixText: 'm²',
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextField(
                      controller: _maxAreaCtrl,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        hintText: 'Área máx. m²',
                        suffixText: 'm²',
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              const Text(
                'Habitaciones / Dormitorios',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    flex: 3,
                    child: _NumberOptionButton(
                      label: 'Todos',
                      selected: _bedrooms == null,
                      onTap: () => setState(() => _bedrooms = null),
                    ),
                  ),
                  const SizedBox(width: 8),
                  ...[1, 2, 3, 4].map((n) {
                    return Expanded(
                      flex: 2,
                      child: Padding(
                        padding: const EdgeInsets.only(left: 4),
                        child: _NumberOptionButton(
                          label: n == 4 ? '4+' : '$n',
                          selected: _bedrooms == n,
                          onTap: () => setState(() => _bedrooms = n),
                        ),
                      ),
                    );
                  }),
                ],
              ),
              const SizedBox(height: 16),

              const Text(
                'Baños completos',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    flex: 3,
                    child: _NumberOptionButton(
                      label: 'Todos',
                      selected: _bathrooms == null,
                      onTap: () => setState(() => _bathrooms = null),
                    ),
                  ),
                  const SizedBox(width: 8),
                  ...[1.0, 2.0, 3.0].map((b) {
                    return Expanded(
                      flex: 2,
                      child: Padding(
                        padding: const EdgeInsets.only(left: 4),
                        child: _NumberOptionButton(
                          label: b == 3.0 ? '3+' : '${b.toInt()}',
                          selected: _bathrooms == b,
                          onTap: () => setState(() => _bathrooms = b),
                        ),
                      ),
                    );
                  }),
                ],
              ),
              const SizedBox(height: 16),

              const Text(
                'Parqueaderos / Garajes',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    flex: 3,
                    child: _NumberOptionButton(
                      label: 'Todos',
                      selected: _parkingSpaces == null,
                      onTap: () => setState(() => _parkingSpaces = null),
                    ),
                  ),
                  const SizedBox(width: 8),
                  ...[1, 2, 3].map((g) {
                    return Expanded(
                      flex: 2,
                      child: Padding(
                        padding: const EdgeInsets.only(left: 4),
                        child: _NumberOptionButton(
                          label: g == 3 ? '3+' : '$g',
                          selected: _parkingSpaces == g,
                          onTap: () => setState(() => _parkingSpaces = g),
                        ),
                      ),
                    );
                  }),
                ],
              ),
              const SizedBox(height: 16),

              Container(
                decoration: BoxDecoration(
                  color: isDark
                      ? const Color(0xFF1E1A3E)
                      : const Color(0xFFF8FAFC),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: isDark ? Colors.white12 : const Color(0xFFE2E8F0),
                  ),
                ),
                child: SwitchListTile.adaptive(
                  activeTrackColor: const Color(0xFFD81F26),
                  activeThumbColor: Colors.white,
                  title: const Text(
                    'Solo Propiedades Exclusivas',
                    style: TextStyle(
                      fontSize: 13.5,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  subtitle: Text(
                    'Inmuebles con contrato de exclusividad Inmobi',
                    style: TextStyle(fontSize: 11.5, color: colors.muted),
                  ),
                  value: _onlyExclusive,
                  onChanged: (v) => setState(() => _onlyExclusive = v),
                ),
              ),
              const SizedBox(height: 22),

              SizedBox(
                width: double.infinity,
                height: 48,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF28235D),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14),
                    ),
                    elevation: 3,
                  ),
                  onPressed: () {
                    final minP = double.tryParse(_minPriceCtrl.text.trim());
                    final maxP = double.tryParse(_maxPriceCtrl.text.trim());
                    final minA = double.tryParse(_minAreaCtrl.text.trim());
                    final maxA = double.tryParse(_maxAreaCtrl.text.trim());
                    widget.onApply(
                      minP,
                      maxP,
                      minA,
                      maxA,
                      _bedrooms,
                      _bathrooms,
                      _parkingSpaces,
                      _sector,
                      _onlyExclusive,
                      _sortOrder,
                    );
                    Navigator.pop(context);
                  },
                  child: const Text(
                    'Aplicar Filtros',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w800,
                      color: Colors.white,
                      letterSpacing: 0.3,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _FilterChoiceChip extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _FilterChoiceChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colors = AppColors.of(context);
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: selected
              ? const Color(0xFF28235D)
              : (isDark ? const Color(0xFF1E1A3E) : const Color(0xFFF1F5F9)),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: selected
                ? const Color(0xFF28235D)
                : (isDark ? Colors.white12 : const Color(0xFFE2E8F0)),
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 12,
            fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
            color: selected
                ? Colors.white
                : (isDark ? Colors.white70 : colors.ink),
          ),
        ),
      ),
    );
  }
}

class _NumberOptionButton extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _NumberOptionButton({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colors = AppColors.of(context);
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          height: 40,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: selected
                ? const Color(0xFF28235D)
                : (isDark ? const Color(0xFF1E1A3E) : const Color(0xFFF1F5F9)),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: selected
                  ? const Color(0xFF28235D)
                  : (isDark ? Colors.white12 : const Color(0xFFE2E8F0)),
              width: selected ? 1.5 : 1.0,
            ),
          ),
          child: Text(
            label,
            style: TextStyle(
              fontSize: 13,
              fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
              color: selected
                  ? Colors.white
                  : (isDark ? Colors.white70 : colors.ink),
            ),
          ),
        ),
      ),
    );
  }
}
