import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../core/api/odoo_client.dart';
import '../../core/config.dart';

/// Estado de sesión de la app. Se expone vía Provider para que cualquier
/// pantalla sepa si hay un usuario logueado y pueda usar [odoo] para
/// consultar datos reales de Inmobi.
///
/// El servidor y la base de datos son fijos (un solo Inmobi, ver
/// [AppConfig]) — el usuario solo inicia sesión con su usuario y contraseña,
/// igual que cualquier app corporativa.
///
/// Nota de alcance (primer corte): no se persiste la sesión entre reinicios
/// de la app — cada apertura pide login de nuevo. Guardarla de forma segura
/// (refresh, biometría, etc.) queda para una siguiente iteración.
class AuthService extends ChangeNotifier {
  final OdooClient odoo = OdooClient();
  final _storage = const FlutterSecureStorage();

  static const _kLogin = 'inmobi_login';

  bool get isAuthenticated => odoo.isAuthenticated;
  String? get userName => odoo.userName;

  Future<String?> loadRememberedLogin() => _storage.read(key: _kLogin);

  Future<void> login({required String login, required String password}) async {
    await odoo.login(
      server: AppConfig.odooServer,
      db: AppConfig.odooDb,
      login: login,
      password: password,
    );
    await _storage.write(key: _kLogin, value: login);
    notifyListeners();
  }

  void logout() {
    odoo.logout();
    notifyListeners();
  }
}
