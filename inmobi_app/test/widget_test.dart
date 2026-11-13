import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';

import 'package:inmobi_app/core/widgets/inmobi_logo.dart';
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
}
