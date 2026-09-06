import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:cookie_jar/cookie_jar.dart';
import 'package:dio_cookie_manager/dio_cookie_manager.dart';
import 'package:flutter/foundation.dart';

import 'odoo_exception.dart';

class OdooClient {
  OdooClient();

  Dio? _dioInstance;
  final CookieJar _cookieJar = CookieJar();

  String? baseUrl;
  String? db;
  int? uid;
  int? get userId => uid;
  String? userName;
  bool isAdmin = false;
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
    isAdmin =
        result['is_admin'] == true ||
        result['is_system'] == true ||
        result['uid'] == 2 ||
        (result['name'] as String? ?? '').toLowerCase().contains('admin');

    if (!isAdmin) await _detectAdminByGroups();
  }

  /// La respuesta de login de Odoo 19 no siempre trae `is_admin`/`is_system`,
  /// y adivinar por el nombre del usuario falla con cuentas como "Inmobi
  /// Bienes Raices": quedaba como no-admin y el CRM le escondía los leads de
  /// los demás asesores. Se le pregunta a Odoo por los grupos reales.
  Future<void> _detectAdminByGroups() async {
    const grupos = [
      'base.group_system',
      'base.group_erp_manager',
      'sales_team.group_sale_manager',
    ];
    for (final grupo in grupos) {
      try {
        final res = await callKw(
          model: 'res.users',
          method: 'has_group',
          args: [
            [uid],
            grupo,
          ],
        );
        if (res == true) {
          isAdmin = true;
          return;
        }
      } catch (_) {
        // El grupo puede no existir si el módulo no está instalado.
      }
    }
  }

  void logout() {
    uid = null;
    userName = null;
    isAdmin = false;
    _cookieJar.deleteAll();
  }

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

  Future<int> create({
    required String model,
    required Map<String, dynamic> values,
  }) async {
    final result = await callKw(model: model, method: 'create', args: [values]);
    return result as int;
  }

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

  Future<void> unlink({required String model, required int id}) async {
    await callKw(
      model: model,
      method: 'unlink',
      args: [
        [id],
      ],
    );
  }

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
