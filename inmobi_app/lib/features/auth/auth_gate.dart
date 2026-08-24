import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../home/home_shell.dart';
import 'auth_service.dart';
import 'login_screen.dart';

/// Decide si mostrar el [HomeShell] (si ya hay sesión activa o se autoinició con éxito)
/// o el [LoginScreen].
class AuthGate extends StatefulWidget {
  const AuthGate({super.key});

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  late Future<bool> _checkAuthFuture;

  @override
  void initState() {
    super.initState();
    final auth = context.read<AuthService>();
    if (auth.isAuthenticated) {
      _checkAuthFuture = Future.value(true);
    } else {
      _checkAuthFuture = auth.tryAutoLogin();
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<bool>(
      future: _checkAuthFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Scaffold(
            backgroundColor: Color(0xFF161338),
            body: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Image(
                    image: AssetImage('assets/branding/logo_white.png'),
                    width: 140,
                    height: 140,
                    fit: BoxFit.contain,
                  ),
                  SizedBox(height: 24),
                  CircularProgressIndicator(
                    color: Color(0xFFF97316),
                  ),
                ],
              ),
            ),
          );
        }

        if (snapshot.data == true) {
          return const HomeShell();
        }

        return const LoginScreen();
      },
    );
  }
}
