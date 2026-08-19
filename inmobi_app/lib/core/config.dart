/// Configuración fija del servidor — es la misma para todos los usuarios
/// de Inmobi, así que no tiene sentido pedírsela a cada uno en el login.
/// Si algún día se prueba contra otro ambiente (staging, local), se cambia
/// aquí una sola vez.
class AppConfig {
  AppConfig._();

  static const String odooServer = 'https://inmobi.tech';
  static const String odooDb = 'inmobi_produccion';
}
