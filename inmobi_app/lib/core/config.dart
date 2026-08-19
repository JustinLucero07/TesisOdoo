/// Configuración fija del servidor — es la misma para todos los usuarios
/// de Inmobi, así que no tiene sentido pedírsela a cada uno en el login.
/// Si algún día se prueba contra otro ambiente (staging, local), se cambia
/// aquí una sola vez.
class AppConfig {
  AppConfig._();

  static const String odooServer = 'https://inmobi.tech';
  static const String odooDb = 'inmobi_produccion';

  /// Sitio público (WordPress/Houzez) al que sincroniza el ERP — se usa
  /// para abrir la publicación de una propiedad desde la app.
  static const String wordpressSite = 'https://inmobi.com.ec';
}
