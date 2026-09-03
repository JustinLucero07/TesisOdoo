import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../core/api/odoo_client.dart';
import '../../core/config.dart';
import '../../core/notifications/notification_service.dart';

/// Estado de sesión de la app. Se expone vía Provider para que cualquier
/// pantalla sepa si hay un usuario logueado y pueda usar [odoo] para
/// consultar datos reales de Inmobi.
class AuthService extends ChangeNotifier {
  final OdooClient odoo = OdooClient();
  final _storage = const FlutterSecureStorage();

  static const _kLogin = 'inmobi_login';
  static const _kPassword = 'inmobi_password';

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

    // Sincroniza el token de notificaciones Push con el usuario en Odoo
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

  /// Intenta iniciar sesión automáticamente con las credenciales guardadas.
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

      await odoo.login(
        server: AppConfig.odooServer,
        db: AppConfig.odooDb,
        login: savedLogin,
        password: savedPassword,
      );

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
    odoo.logout();
    notifyListeners();
  }
}

