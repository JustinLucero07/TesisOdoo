class OdooException implements Exception {
  final String message;
  final String? debugInfo;

  /// true cuando no se llegó al servidor (sin internet, timeout): en ese caso
  /// se puede mostrar lo último guardado en el celular.
  final bool isNetwork;

  OdooException(this.message, {this.debugInfo, this.isNetwork = false});

  @override
  String toString() => message;
}
