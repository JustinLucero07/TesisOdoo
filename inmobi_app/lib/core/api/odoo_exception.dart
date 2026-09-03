class OdooException implements Exception {
  final String message;
  final String? debugInfo;

  OdooException(this.message, {this.debugInfo});

  @override
  String toString() => message;
}
