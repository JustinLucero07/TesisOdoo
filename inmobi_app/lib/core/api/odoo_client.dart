import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:cookie_jar/cookie_jar.dart';
import 'package:dio_cookie_manager/dio_cookie_manager.dart';
import 'package:flutter/foundation.dart';

import 'odoo_exception.dart';

/// Cliente para el backend de Odoo, vía el mismo protocolo JSON-RPC que usa
/// el cliente web nativo de Odoo (POST a /web/session/authenticate y
/// /web/dataset/call_kw). No requiere ningún módulo/endpoint nuevo en Odoo:
/// funciona contra el sistema tal como está hoy.
///
/// Autenticación por sesión (cookie), no por token — por eso se usa un
/// [CookieJar] compartido entre requests.
class OdooClient {
  OdooClient();

  Dio? _dioInstance;
  final CookieJar _cookieJar = CookieJar();

  String? baseUrl;
  String? db;
  int? uid;
  String? userName;
  bool get isAuthenticated => uid != null;

  void _ensureDio(String baseUrl) {
    if (_dioInstance != null && _dioInstance!.options.baseUrl == baseUrl)
      return;
    final dio = Dio(
      BaseOptions(
        baseUrl: baseUrl,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 30),
        headers: {'Content-Type': 'application/json'},
      ),
    );
    dio.interceptors.add(CookieManager(_cookieJar));
    if (kDebugMode) {
      dio.interceptors.add(
        LogInterceptor(requestBody: true, responseBody: true),
      );
    }
    _dioInstance = dio;
  }

  Dio get client {
    final dio = _dioInstance;
    if (dio == null) {
      throw OdooException(
        'No hay conexión configurada. Inicia sesión primero.',
      );
    }
    return dio;
  }

  Future<Map<String, dynamic>> _rpc(
    String path,
    Map<String, dynamic> params,
  ) async {
    try {
      final resp = await client.post(
        path,
        data: {'jsonrpc': '2.0', 'method': 'call', 'params': params},
      );
      if (resp.data is! Map<String, dynamic>) {
        // El servidor respondió algo que no es JSON (ej. una página de error
        // de Nginx/Odoo) — con un mensaje claro en vez de un cast que revienta.
        throw OdooException(
          'El servidor respondió algo inesperado (${resp.statusCode}).',
        );
      }
      final data = resp.data as Map<String, dynamic>;
      if (data['error'] != null) {
        final err = data['error'];
        final msg =
            err['data']?['message'] ?? err['message'] ?? 'Error del servidor';
        throw OdooException(
          msg.toString(),
          debugInfo: err['data']?['debug']?.toString(),
        );
      }
      return data;
    } on DioException catch (e) {
      if (e.type == DioExceptionType.connectionTimeout ||
          e.type == DioExceptionType.connectionError) {
        throw OdooException(
          'No se pudo conectar al servidor. Revisa la URL y tu conexión.',
        );
      }
      rethrow;
    }
  }

  /// Autentica contra Odoo y guarda la sesión (cookie) para las siguientes
  /// llamadas. [server] debe incluir el esquema, ej. https://tuservidor.com.
  Future<void> login({
    required String server,
    required String db,
    required String login,
    required String password,
  }) async {
    final normalized = server.endsWith('/')
        ? server.substring(0, server.length - 1)
        : server;
    _ensureDio(normalized);
    final data = await _rpc('/web/session/authenticate', {
      'db': db,
      'login': login,
      'password': password,
    });
    final result = data['result'] as Map<String, dynamic>?;
    if (result == null || result['uid'] == null) {
      throw OdooException('Usuario o contraseña incorrectos.');
    }
    baseUrl = normalized;
    this.db = db;
    uid = result['uid'] as int;
    userName = result['name'] as String? ?? login;
  }

  void logout() {
    uid = null;
    userName = null;
    _cookieJar.deleteAll();
  }

  /// Ejecuta un método del ORM de Odoo (search_read, read, write, etc.),
  /// igual que hace el cliente web. Respeta los permisos del usuario logueado.
  Future<dynamic> callKw({
    required String model,
    required String method,
    List<dynamic> args = const [],
    Map<String, dynamic> kwargs = const {},
  }) async {
    if (!isAuthenticated) {
      throw OdooException('Sesión no iniciada.');
    }
    final data = await _rpc('/web/dataset/call_kw', {
      'model': model,
      'method': method,
      'args': args,
      'kwargs': kwargs,
    });
    return data['result'];
  }

  Future<List<Map<String, dynamic>>> searchRead({
    required String model,
    List<dynamic> domain = const [],
    List<String> fields = const [],
    int? limit,
    int? offset,
    String? order,
  }) async {
    final result = await callKw(
      model: model,
      method: 'search_read',
      args: [domain, fields],
      kwargs: {
        if (limit != null) 'limit': limit,
        if (offset != null) 'offset': offset,
        if (order != null) 'order': order,
      },
    );
    return (result as List).cast<Map<String, dynamic>>();
  }

  /// Crea un registro nuevo — igual que hacer "Guardar" en un formulario del
  /// ERP. Devuelve el id creado. Respeta permisos/validaciones del modelo.
  Future<int> create({
    required String model,
    required Map<String, dynamic> values,
  }) async {
    final result = await callKw(model: model, method: 'create', args: [values]);
    return result as int;
  }

  /// Edita un registro existente — igual que "Guardar" tras modificar un
  /// formulario ya abierto.
  Future<void> write({
    required String model,
    required int id,
    required Map<String, dynamic> values,
  }) async {
    await callKw(
      model: model,
      method: 'write',
      args: [
        [id],
        values,
      ],
    );
  }

  /// Elimina un registro — mismo `unlink` del ORM, con sus validaciones
  /// (si el modelo lo impide, Odoo devuelve el error y se propaga).
  Future<void> unlink({required String model, required int id}) async {
    await callKw(
      model: model,
      method: 'unlink',
      args: [
        [id],
      ],
    );
  }

  /// Descarga un PDF generado por un reporte QWeb de Odoo, vía la ruta
  /// nativa `/report/pdf/<reporte>/<ids>`. Los parámetros extra del reporte
  /// (ej. el diseño de la ficha) viajan en `options` como JSON, para que
  /// lleguen con su tipo real (bool/int) y no como texto.
  Future<Uint8List> downloadReportPdf({
    required String reportName,
    required int id,
    Map<String, dynamic> options = const {},
  }) async {
    final resp = await client.get<List<int>>(
      '/report/pdf/$reportName/$id',
      queryParameters: options.isEmpty
          ? null
          : {'options': jsonEncode(options)},
      options: Options(responseType: ResponseType.bytes),
    );
    return Uint8List.fromList(resp.data ?? const []);
  }

  /// Descarga el valor de un campo binario (imagen de galería, PDF de un
  /// documento, etc.) vía el endpoint nativo `/web/content/<model>/<id>/<field>`
  /// — mismo mecanismo que usa el cliente web para descargar adjuntos, sin
  /// necesidad de traer el archivo en base64 dentro de un `read`/`search_read`.
  Future<Uint8List> downloadBytes({
    required String model,
    required int id,
    required String field,
  }) async {
    final resp = await client.get<List<int>>(
      '/web/content/$model/$id/$field',
      options: Options(responseType: ResponseType.bytes),
    );
    return Uint8List.fromList(resp.data ?? const []);
  }
}
