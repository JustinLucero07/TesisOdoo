import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:provider/provider.dart';

import 'core/theme/app_theme.dart';
import 'features/auth/auth_service.dart';
import 'features/auth/login_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Sin esto, cualquier DateFormat/NumberFormat con locale 'es_EC' revienta
  // con LocaleDataException apenas arranca la app.
  await initializeDateFormatting('es_EC', null);
  runApp(const InmobiApp());
}

class InmobiApp extends StatelessWidget {
  const InmobiApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => AuthService(),
      child: MaterialApp(
        title: 'Inmobi',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.light(),
        locale: const Locale('es', 'EC'),
        supportedLocales: const [Locale('es', 'EC'), Locale('es')],
        localizationsDelegates: const [
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        home: const LoginScreen(),
      ),
    );
  }
}
