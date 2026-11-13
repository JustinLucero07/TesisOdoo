import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_motion.dart';
import '../../core/widgets/inmobi_logo.dart';
import '../home/home_shell.dart';
import 'auth_service.dart';
import 'login_screen.dart';

class AuthGate extends StatefulWidget {
  const AuthGate({super.key});

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  bool? _loggedIn;
  bool _animationDone = false;

  @override
  void initState() {
    super.initState();
    final auth = context.read<AuthService>();
    final check = auth.isAuthenticated
        ? Future.value(true)
        : auth.tryAutoLogin();
    check.then((ok) {
      if (mounted) setState(() => _loggedIn = ok);
    });
  }

  @override
  Widget build(BuildContext context) {
    // Se queda en la pantalla de carga hasta que termine la animación del
    // logo Y se sepa si hay sesión: así la animación nunca se corta a medias.
    final ready = _loggedIn != null && _animationDone;
    final Widget child;
    if (!ready) {
      child = _SplashScreen(
        key: const ValueKey('splash'),
        waiting: _animationDone,
        onAnimationDone: () {
          if (mounted) setState(() => _animationDone = true);
        },
      );
    } else if (_loggedIn == true) {
      child = const HomeShell(key: ValueKey('home'));
    } else {
      child = const LoginScreen(key: ValueKey('login'));
    }

    return AnimatedSwitcher(
      duration: AppMotion.duration(context, const Duration(milliseconds: 450)),
      switchInCurve: Curves.easeOutCubic,
      switchOutCurve: Curves.easeInCubic,
      child: child,
    );
  }
}

class _SplashScreen extends StatefulWidget {
  const _SplashScreen({
    super.key,
    required this.waiting,
    required this.onAnimationDone,
  });

  /// La animación ya terminó pero todavía se está iniciando sesión.
  final bool waiting;
  final VoidCallback onAnimationDone;

  @override
  State<_SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<_SplashScreen>
    with SingleTickerProviderStateMixin {
  // La diagonal del fondo entra antes que el techo.
  late final AnimationController _bg = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 700),
  );

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (AppMotion.reduced(context)) {
      _bg.value = 1;
    } else if (!_bg.isAnimating && _bg.value == 0) {
      _bg.forward();
    }
  }

  @override
  void dispose() {
    _bg.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    return Scaffold(
      body: AnimatedBuilder(
        animation: _bg,
        builder: (context, child) =>
            InmobiDiagonalBackground(reveal: _bg.value, child: child),
        child: SizedBox.expand(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              AnimatedInmobiLogo(
                width: (width * 0.62).clamp(180.0, 280.0),
                delay: const Duration(milliseconds: 250),
                duration: const Duration(milliseconds: 1500),
                onFinished: widget.onAnimationDone,
              ),
              const SizedBox(height: 44),
              AnimatedOpacity(
                opacity: widget.waiting ? 1 : 0,
                duration: const Duration(milliseconds: 300),
                child: const InmobiLoadingBar(width: 110),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
