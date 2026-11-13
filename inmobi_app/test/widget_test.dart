import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';

import 'package:inmobi_app/core/app_startup.dart';
import 'package:inmobi_app/core/widgets/inmobi_logo.dart';
import 'package:inmobi_app/features/auth/auth_gate.dart';
import 'package:inmobi_app/features/auth/auth_service.dart';
import 'package:inmobi_app/features/home/home_shell.dart';
import 'package:inmobi_app/main.dart';

void main() {
  testWidgets('Arranca con el logo animado y sigue al login', (tester) async {
    await initializeDateFormatting('es_EC', null);
    // Sin sesión guardada en el teléfono.
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
          const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
          (call) async => null,
        );
    await tester.pumpWidget(const InmobiApp());

    // Pantalla de carga: el logo dibujado.
    expect(find.byType(AnimatedInmobiLogo), findsOneWidget);

    // Sin sesión guardada, al terminar la animación pasa al login.
    for (var i = 0; i < 12; i++) {
      await tester.pump(const Duration(milliseconds: 300));
    }
    expect(find.text('Bienvenido'), findsOneWidget);
    expect(find.text('Ingresar al Sistema'), findsOneWidget);
  });

  testWidgets('Con sesión, el logo se queda hasta que el inicio cargó', (
    tester,
  ) async {
    await initializeDateFormatting('es_EC', null);
    _mockPlugins(Directory.systemTemp.createTempSync('inmobi_test'));
    AppStartup.homeReady.value = false;
    final auth = AuthService();
    // Sesión abierta (sin servidor real: el panel no podrá traer datos y
    // avisará igual que terminó de intentar).
    auth.odoo.restoreOffline(
      server: 'http://127.0.0.1:9',
      db: 'x',
      uid: 2,
      userName: 'Prueba',
      isAdmin: false,
    );
    await tester.pumpWidget(
      ChangeNotifierProvider.value(
        value: auth,
        child: const MaterialApp(home: AuthGate()),
      ),
    );

    // Mientras tanto se ve el logo y el círculo de carga, encima del inicio.
    await tester.pump(const Duration(milliseconds: 600));
    expect(find.byType(AnimatedInmobiLogo), findsOneWidget);
    expect(find.byType(CircularProgressIndicator), findsWidgets);
    expect(find.byType(HomeShell), findsOneWidget);

    // Cuando el inicio avisa que está listo y la animación terminó, se va.
    AppStartup.homeReady.value = true;
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 300));
    }
    final splash = tester.widget<IgnorePointer>(
      find
          .ancestor(
            of: find.byType(AnimatedInmobiLogo),
            matching: find.byType(IgnorePointer),
          )
          .first,
    );
    expect(
      splash.ignoring,
      isTrue,
      reason: 'la pantalla del logo ya no tapa el inicio',
    );
  });
}

void _mockPlugins(Directory tmp) {
  final m = TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;
  m.setMockMethodCallHandler(
    const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
    (call) async => null,
  );
  m.setMockMethodCallHandler(
    const MethodChannel('plugins.flutter.io/path_provider'),
    (call) async => tmp.path,
  );
  m.setMockMethodCallHandler(
    const MethodChannel('dexterous.com/flutter/local_notifications'),
    (call) async => null,
  );
}
