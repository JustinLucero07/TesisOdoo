import '../../core/api/odoo_client.dart';
import 'property_model.dart';

/// Consulta propiedades reales de `estate.property` vía ORM (search_read),
/// respetando los permisos del usuario con soporte para filtros y caché offline.
class PropertyService {
  final OdooClient odoo;
  PropertyService(this.odoo);

  static List<Property> _cachedPropertyList = [];
  static final Map<int, Property> _cachedDetails = {};

  static List<Property> get cachedList => List.unmodifiable(_cachedPropertyList);

  Future<List<Property>> list({
    String? searchText,
    List<String>? states,
    String? offerType,
    double? minPrice,
    double? maxPrice,
    int? bedrooms,
    double? bathrooms,
    int? propertyTypeId,
    bool? isExclusive,
    String? city,
    String? sector,
    double? minArea,
    double? maxArea,
    int? parkingSpaces,
    String order = 'create_date desc',
    int limit = 50,
    int offset = 0,
  }) async {
    final domain = <dynamic>[];

    if (searchText != null && searchText.trim().isNotEmpty) {
      final text = searchText.trim();
      domain.addAll([
        '|',
        '|',
        '|',
        ['title', 'ilike', text],
        ['city', 'ilike', text],
        ['sector', 'ilike', text],
        ['reference', 'ilike', text],
      ]);
    }
    if (states != null && states.isNotEmpty) {
      domain.add(['state', 'in', states]);
    }
    if (offerType != null) {
      domain.add(['offer_type', '=', offerType]);
    }
    if (minPrice != null && minPrice > 0) {
      domain.add(['sale_price', '>=', minPrice]);
    }
    if (maxPrice != null && maxPrice > 0) {
      domain.add(['sale_price', '<=', maxPrice]);
    }
    if (minArea != null && minArea > 0) {
      domain.add(['area', '>=', minArea]);
    }
    if (maxArea != null && maxArea > 0) {
      domain.add(['area', '<=', maxArea]);
    }
    if (parkingSpaces != null && parkingSpaces > 0) {
      if (parkingSpaces >= 3) {
        domain.add(['garage', '>=', 3]);
      } else {
        domain.add(['garage', '=', parkingSpaces]);
      }
    }
    if (bedrooms != null && bedrooms > 0) {
      if (bedrooms >= 4) {
        domain.add(['bedrooms', '>=', 4]);
      } else {
        domain.add(['bedrooms', '=', bedrooms]);
      }
    }
    if (bathrooms != null && bathrooms > 0) {
      domain.add(['bathrooms', '>=', bathrooms]);
    }
    if (propertyTypeId != null) {
      domain.add(['property_type_id', '=', propertyTypeId]);
    }
    if (isExclusive == true) {
      domain.add(['is_exclusive', '=', true]);
    }
    if (city != null && city.trim().isNotEmpty) {
      domain.add(['city', 'ilike', city.trim()]);
    }
    if (sector != null && sector.trim().isNotEmpty) {
      domain.add(['sector', 'ilike', sector.trim()]);
    }

    try {
      final rows = await odoo.searchRead(
        model: 'estate.property',
        domain: domain,
        fields: Property.listFields,
        limit: limit,
        offset: offset,
        order: order,
      );
      final list = rows.map(Property.fromJson).toList();
      if (offset == 0 && (searchText == null || searchText.isEmpty) && (states == null || states.isEmpty)) {
        _cachedPropertyList = list;
      }
      return list;
    } catch (e) {
      // Fallback offline a partir de los datos cacheados
      if (_cachedPropertyList.isNotEmpty) {
        var filtered = _cachedPropertyList;
        if (searchText != null && searchText.trim().isNotEmpty) {
          final query = searchText.trim().toLowerCase();
          filtered = filtered
              .where((p) =>
                  p.title.toLowerCase().contains(query) ||
                  p.city.toLowerCase().contains(query) ||
                  p.sector.toLowerCase().contains(query) ||
                  p.reference.toLowerCase().contains(query))
              .toList();
        }
        if (states != null && states.isNotEmpty) {
          filtered = filtered.where((p) => states.contains(p.state)).toList();
        }
        return filtered;
      }
      rethrow;
    }
  }

  Future<Property> detail(int id) async {
    try {
      final rows = await odoo.searchRead(
        model: 'estate.property',
        domain: [
          ['id', '=', id],
        ],
        fields: Property.detailFields,
        limit: 1,
      );
      final prop = Property.fromJson(rows.first);
      _cachedDetails[id] = prop;
      return prop;
    } catch (e) {
      if (_cachedDetails.containsKey(id)) {
        return _cachedDetails[id]!;
      }
      rethrow;
    }
  }

  Future<int> create(Map<String, dynamic> values) =>
      odoo.create(model: 'estate.property', values: values);

  Future<void> update(int id, Map<String, dynamic> values) =>
      odoo.write(model: 'estate.property', id: id, values: values);
}
