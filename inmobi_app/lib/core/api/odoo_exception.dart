/// Error devuelto por el servidor Odoo (login inválido, permisos, error de
/// negocio lanzado con UserError, etc.) — se distingue de errores de red
/// para poder mostrar un mensaje claro al usuario en vez de "algo salió mal".
class OdooException implements Exception {
  final String message;
  final String? debugInfo;

  OdooException(this.message, {this.debugInfo});

  @override
  String toString() => message;
}
