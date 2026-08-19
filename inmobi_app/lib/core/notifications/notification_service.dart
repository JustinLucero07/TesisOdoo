import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_timezone/flutter_timezone.dart';
import 'package:timezone/data/latest_all.dart' as tzdata;
import 'package:timezone/timezone.dart' as tz;

/// Notificaciones de las citas en el propio teléfono.
///
/// Son notificaciones LOCALES: la app las programa en el dispositivo cuando
/// carga la agenda, y el sistema operativo las dispara a la hora indicada
/// aunque la app esté cerrada y sin conexión. Es distinto del recordatorio
/// por WhatsApp que manda el ERP: aquel avisa al cliente y al asesor por
/// mensaje; este es la alarma personal del asesor en su celular.
///
/// Al ser locales, solo cubren las citas que la app alcanzó a ver: si se
/// crea una cita desde el ERP y el asesor no abre la app, esa no queda
/// programada. Para eso haría falta notificación push (servidor + Firebase).
class NotificationService {
  NotificationService._();
  static final instance = NotificationService._();

  static const _prefKey = 'inmobi_notifications_enabled';
  static const _channelId = 'inmobi_visitas';

  final _plugin = FlutterLocalNotificationsPlugin();
  final _storage = const FlutterSecureStorage();

  bool _ready = false;
  bool _enabled = true;
  bool get enabled => _enabled;

  Future<void> init() async {
    if (_ready) return;
    try {
      tzdata.initializeTimeZones();
      // Sin la zona local correcta, una cita de las 15:00 se programaría en
      // UTC y sonaría a la hora equivocada.
      final localName = await FlutterTimezone.getLocalTimezone();
      tz.setLocalLocation(tz.getLocation(localName.identifier));
    } catch (e) {
      debugPrint('Zona horaria no resuelta, se usa la de por defecto: $e');
    }

    const android = AndroidInitializationSettings('@mipmap/ic_launcher');
    const darwin = DarwinInitializationSettings(
      requestAlertPermission: false,
      requestBadgePermission: false,
      requestSoundPermission: false,
    );
    try {
      await _plugin.initialize(
        settings: const InitializationSettings(
          android: android,
          iOS: darwin,
          macOS: darwin,
        ),
      );
      _ready = true;
    } catch (e) {
      debugPrint('No se pudieron inicializar las notificaciones: $e');
    }

    final saved = await _storage.read(key: _prefKey);
    _enabled = saved != 'false';
  }

  /// Pide el permiso del sistema. En Android 13+ y en iOS es obligatorio
  /// preguntarlo antes de poder mostrar nada.
  Future<bool> requestPermission() async {
    if (!_ready) await init();
    try {
      final android = _plugin
          .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin
          >();
      if (android != null) {
        final granted = await android.requestNotificationsPermission();
        return granted ?? false;
      }
      final ios = _plugin
          .resolvePlatformSpecificImplementation<
            IOSFlutterLocalNotificationsPlugin
          >();
      if (ios != null) {
        final granted = await ios.requestPermissions(
          alert: true,
          badge: true,
          sound: true,
        );
        return granted ?? false;
      }
    } catch (e) {
      debugPrint('Permiso de notificaciones no concedido: $e');
    }
    return false;
  }

  Future<void> setEnabled(bool value) async {
    _enabled = value;
    await _storage.write(key: _prefKey, value: value ? 'true' : 'false');
    if (!value) await cancelAll();
  }

  /// Programa el aviso de una cita. [minutesBefore] es la anticipación; si la
  /// hora resultante ya pasó, no se programa nada (el sistema descartaría un
  /// disparo en el pasado).
  Future<void> scheduleVisit({
    required int visitId,
    required String title,
    required String body,
    required DateTime start,
    required int minutesBefore,
  }) async {
    if (!_ready || !_enabled) return;
    final when = start.subtract(Duration(minutes: minutesBefore));
    if (!when.isAfter(DateTime.now())) return;

    const details = NotificationDetails(
      android: AndroidNotificationDetails(
        _channelId,
        'Recordatorios de citas',
        channelDescription:
            'Avisos de las visitas y citas agendadas en Inmobi.',
        importance: Importance.high,
        priority: Priority.high,
        icon: '@mipmap/ic_launcher',
      ),
      iOS: DarwinNotificationDetails(),
    );

    try {
      await _plugin.zonedSchedule(
        // El id de la cita es el id de la notificación: reprogramarla
        // reemplaza la anterior en vez de duplicar el aviso.
        id: visitId,
        title: title,
        body: body,
        scheduledDate: tz.TZDateTime.from(when, tz.local),
        notificationDetails: details,
        androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      );
    } catch (e) {
      debugPrint(
        'No se pudo programar la notificación de la cita $visitId: $e',
      );
    }
  }

  Future<void> cancelVisit(int visitId) async {
    if (!_ready) return;
    try {
      await _plugin.cancel(id: visitId);
    } catch (e) {
      debugPrint('No se pudo cancelar la notificación $visitId: $e');
    }
  }

  Future<void> cancelAll() async {
    if (!_ready) return;
    try {
      await _plugin.cancelAll();
    } catch (e) {
      debugPrint('No se pudieron cancelar las notificaciones: $e');
    }
  }

  Future<List<PendingNotificationRequest>> pending() async {
    if (!_ready) return const [];
    try {
      return await _plugin.pendingNotificationRequests();
    } catch (_) {
      return const [];
    }
  }
}
