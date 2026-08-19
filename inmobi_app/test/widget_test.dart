import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:inmobi_app/main.dart';

void main() {
  testWidgets('La app arranca en la pantalla de login', (WidgetTester tester) async {
    await tester.pumpWidget(const InmobiApp());
    expect(find.text('Gestión Inmobiliaria'), findsOneWidget);
    expect(find.widgetWithText(ElevatedButton, 'Iniciar sesión'), findsOneWidget);
  });
}
