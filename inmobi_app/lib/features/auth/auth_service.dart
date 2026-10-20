import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../core/api/odoo_client.dart';
import '../../core/api/odoo_exception.dart';
import '../../core/config.dart';
import '../../core/notifications/notification_service.dart';

class AuthService extends ChangeNotifier {
  final OdooClient odoo = OdooClient();
  final _storage = const FlutterSecureStorage();

  static const _kLogin = 'inmobi_login';
  static const _kPassword = 'inmobi_password';
  // Datos del último inicio de sesión, para poder abrir la app sin internet.
  static const _kSession = 'inmobi_last_session';

  AuthService() {
    odoo.reauthenticate = _relogin;
  }

  Future<void> _relogin() async {
    final savedLogin = await _storage.read(key: _kLogin);
    final savedPassword = await _storage.read(key: _kPassword);
    if (savedLogin == null || savedPassword == null) return;
    await odoo.login(
      server: AppConfig.odooServer,
      db: AppConfig.odooDb,
      login: savedLogin,
      password: savedPassword,
    );
  }

  Future<void> _saveSession() async {
    if (odoo.userId == null) return;
    await _storage.write(
      key: _kSession,
      value: jsonEncode({
        'uid': odoo.userId,
        'name': odoo.userName,
        'admin': odoo.isAdmin,
      }),
    );
  }

  /// Sin internet: abre la app con la última sesión y los datos guardados.
  Future<bool> _restoreOfflineSession() async {
    final raw = await _storage.read(key: _kSession);
    if (raw == null) return false;
    try {
      final data = jsonDecode(raw) as Map<String, dynamic>;
      odoo.restoreOffline(
        server: AppConfig.odooServer,
        db: AppConfig.odooDb,
        uid: data['uid'] as int,
        userName: data['name'] as String?,
        isAdmin: data['admin'] == true,
      );
      notifyListeners();
      return true;
    } catch (_) {
      return false;
    }
  }

  bool get isAuthenticated => odoo.isAuthenticated;
  String? get userName => odoo.userName;
  bool get isAdmin => odoo.isAdmin;

  Future<String?> loadRememberedLogin() => _storage.read(key: _kLogin);

  Future<void> login({required String login, required String password}) async {
    await odoo.login(
      server: AppConfig.odooServer,
      db: AppConfig.odooDb,
      login: login,
      password: password,
    );
    await _storage.write(key: _kLogin, value: login);
    await _storage.write(key: _kPassword, value: password);
    await _saveSession();

    if (odoo.userId != null) {
      unawaited(
        NotificationService.instance.syncTokenWithOdoo(
          odoo: odoo,
          userId: odoo.userId!,
        ),
      );
    }

    notifyListeners();
  }

  Future<bool> tryAutoLogin() async {
    try {
      final savedLogin = await _storage.read(key: _kLogin);
      final savedPassword = await _storage.read(key: _kPassword);
      if (savedLogin == null ||
          savedLogin.isEmpty ||
          savedPassword == null ||
          savedPassword.isEmpty) {
        return false;
      }

      try {
        await odoo.login(
          server: AppConfig.odooServer,
          db: AppConfig.odooDb,
          login: savedLogin,
          password: savedPassword,
        );
      } on OdooException catch (e) {
        if (e.isNetwork) return _restoreOfflineSession();
        rethrow;
      }
      await _saveSession();

      if (odoo.userId != null) {
        unawaited(
          NotificationService.instance.syncTokenWithOdoo(
            odoo: odoo,
            userId: odoo.userId!,
          ),
        );
      }

      notifyListeners();
      return true;
    } catch (e) {
      return false;
    }
  }

  Future<void> logout() async {
    await _storage.delete(key: _kPassword);
    await _storage.delete(key: _kSession);
    odoo.logout();
    notifyListeners();
  }
}
