import 'dart:async';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_timezone/flutter_timezone.dart';
import 'package:timezone/data/latest_all.dart' as tzdata;
import 'package:timezone/timezone.dart' as tz;

import '../api/odoo_client.dart';

@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
}

/// Servicio integral de Notificaciones Locales y Notificaciones Push con Firebase (FCM).
class NotificationService {
  NotificationService._();
  static final instance = NotificationService._();

  static const _prefKey = 'inmobi_notifications_enabled';
  static const _channelId = 'inmobi_visitas';
  static const _channelName = 'Inmobi Notificaciones';

  final _plugin = FlutterLocalNotificationsPlugin();
  final _storage = const FlutterSecureStorage();

  bool _ready = false;
  bool _enabled = true;
  String? _fcmToken;

  bool get enabled => _enabled;
  String? get fcmToken => _fcmToken;

  Future<void> init() async {
    if (_ready) return;

    // 1. Inicializar Timezones para alarmas locales
    try {
      tzdata.initializeTimeZones();
      final localName = await FlutterTimezone.getLocalTimezone();
      tz.setLocalLocation(tz.getLocation(localName.identifier));
    } catch (_) {
      // Sin zona horaria resuelta las alarmas usan la del sistema.
    }

    // 2. Inicializar Flutter Local Notifications Plugin
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

      // Crear canal de notificación para Android
      final androidPlugin = _plugin.resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin>();
      if (androidPlugin != null) {
        await androidPlugin.createNotificationChannel(
          const AndroidNotificationChannel(
            _channelId,
            _channelName,
            description: 'Canal de avisos y notificaciones push de Inmobi.',
            importance: Importance.high,
            playSound: true,
          ),
        );
      }
    } catch (_) {
      // Sin notificaciones locales la app sigue funcionando igual.
    }

    // 3. Inicializar Firebase y FCM (solo en Android e iOS)
    if (!kIsWeb && (defaultTargetPlatform == TargetPlatform.android || defaultTargetPlatform == TargetPlatform.iOS)) {
      try {
        await Firebase.initializeApp();
        FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);

        // Escuchar notificaciones en primer plano y mostrarlas con LocalNotifications
        FirebaseMessaging.onMessage.listen((RemoteMessage message) {
          final notification = message.notification;
          if (notification != null) {
            showNotification(
              id: message.hashCode,
              title: notification.title ?? 'Inmobi',
              body: notification.body ?? '',
            );
          }
        });

        // Obtener el token FCM inicial
        _fcmToken = await FirebaseMessaging.instance.getToken();

        // Escuchar cambios de token
        FirebaseMessaging.instance.onTokenRefresh.listen((newToken) {
          _fcmToken = newToken;
        });
      } catch (_) {
        // Sin Firebase no hay push, pero el resto de la app funciona.
      }
    }

    final saved = await _storage.read(key: _prefKey);
    _enabled = saved != 'false';
    _ready = true;
  }

  /// Pide permisos al usuario tanto para notificaciones locales como FCM
  Future<bool> requestPermission() async {
    if (!_ready) await init();

    try {
      if (!kIsWeb && (defaultTargetPlatform == TargetPlatform.android || defaultTargetPlatform == TargetPlatform.iOS)) {
        final settings = await FirebaseMessaging.instance.requestPermission(
          alert: true,
          badge: true,
          sound: true,
          provisional: false,
        );
        if (settings.authorizationStatus == AuthorizationStatus.authorized ||
            settings.authorizationStatus == AuthorizationStatus.provisional) {
          return true;
        }
      }

      final android = _plugin.resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin>();
      if (android != null) {
        final granted = await android.requestNotificationsPermission();
        return granted ?? false;
      }
    } catch (_) {
      // Permiso denegado o no disponible en esta plataforma.
    }
    return false;
  }

  /// Sincroniza el FCM Token con el backend Odoo
  Future<void> syncTokenWithOdoo({
    required OdooClient odoo,
    required int userId,
  }) async {
    try {
      if (_fcmToken == null && !kIsWeb && (defaultTargetPlatform == TargetPlatform.android || defaultTargetPlatform == TargetPlatform.iOS)) {
        _fcmToken = await FirebaseMessaging.instance.getToken();
      }

      if (_fcmToken != null && _fcmToken!.isNotEmpty) {
        await odoo.write(
          model: 'res.users',
          id: userId,
          values: {'fcm_token': _fcmToken},
        );
      }
    } catch (_) {
      // El token se reintenta en el próximo arranque.
    }
  }

  Future<void> setEnabled(bool value) async {
    _enabled = value;
    await _storage.write(key: _prefKey, value: value ? 'true' : 'false');
    if (!value) await cancelAll();
  }

  /// Muestra una notificación inmediata
  Future<void> showNotification({
    required int id,
    required String title,
    required String body,
  }) async {
    if (!_ready || !_enabled) return;

    const details = NotificationDetails(
      android: AndroidNotificationDetails(
        _channelId,
        _channelName,
        importance: Importance.high,
        priority: Priority.high,
        icon: '@drawable/ic_notification',
        color: Color(0xFFD81F26),
      ),
      iOS: DarwinNotificationDetails(),
    );

    await _plugin.show(
      id: id,
      title: title,
      body: body,
      notificationDetails: details,
    );
  }

  /// Programa una notificación de cita local
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
        _channelName,
        importance: Importance.high,
        priority: Priority.high,
        icon: '@drawable/ic_notification',
        color: Color(0xFFD81F26),
      ),
      iOS: DarwinNotificationDetails(),
    );

    try {
      final scheduledDate = tz.TZDateTime.from(when, tz.local);
      await _plugin.zonedSchedule(
        id: visitId,
        title: title,
        body: body,
        scheduledDate: scheduledDate,
        notificationDetails: details,
        androidScheduleMode: AndroidScheduleMode.exactAllowWhileIdle,
      );
    } catch (e) {
      try {
        await _plugin.zonedSchedule(
          id: visitId,
          title: title,
          body: body,
          scheduledDate: tz.TZDateTime.from(when, tz.local),
          notificationDetails: details,
          androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
        );
      } catch (_) {
        // Ni exacta ni inexacta: el aviso local no se pudo programar.
      }
    }
  }

  Future<void> cancelVisit(int visitId) async => _plugin.cancel(id: visitId);
  Future<void> cancelAll() async => _plugin.cancelAll();

  Future<List<PendingNotificationRequest>> pending() async {
    if (!_ready) return const [];
    try {
      return await _plugin.pendingNotificationRequests();
    } catch (_) {
      return const [];
    }
  }
}
