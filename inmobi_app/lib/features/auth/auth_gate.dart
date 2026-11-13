import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/app_startup.dart';
import '../../core/theme/app_motion.dart';
import '../../core/theme/app_theme.dart';
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
  bool _homeReady = false;
  Timer? _timeout;

  // Si el inicio tarda demasiado (internet muy lento) se entra igual: el
  // panel muestra su propio estado de carga.
  static const _maxWait = Duration(seconds: 12);

  @override
  void initState() {
    super.initState();
    AppStartup.homeReady.addListener(_onHomeReady);
    _homeReady = AppStartup.homeReady.value;
    final auth = context.read<AuthService>();
    final check = auth.isAuthenticated
        ? Future.value(true)
        : auth.tryAutoLogin();
    check.then((ok) {
      if (!mounted) return;
      setState(() => _loggedIn = ok);
      if (ok) {
        _timeout = Timer(_maxWait, () {
          if (mounted) setState(() => _homeReady = true);
        });
      }
    });
  }

  void _onHomeReady() {
    if (AppStartup.homeReady.value && mounted) {
      setState(() => _homeReady = true);
    }
  }

  @override
  void dispose() {
    AppStartup.homeReady.removeListener(_onHomeReady);
    _timeout?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // La pantalla del logo se queda mientras: corre la animación, se revisa
    // la sesión y, si hay sesión, el inicio trae sus datos (el inicio se va
    // armando detrás). Así nunca queda una pantalla en blanco con un círculo.
    final sessionKnown = _loggedIn != null;
    final showSplash =
        !_animationDone ||
        !sessionKnown ||
        (_loggedIn == true && !_homeReady);

    final Widget base = !sessionKnown
        ? const SizedBox.shrink()
        : (_loggedIn == true
              ? const HomeShell(key: ValueKey('home'))
              : const LoginScreen(key: ValueKey('login')));

    return Stack(
      children: [
        Positioned.fill(child: base),
        Positioned.fill(
          child: IgnorePointer(
            ignoring: !showSplash,
            child: AnimatedOpacity(
              opacity: showSplash ? 1 : 0,
              duration: AppMotion.duration(
                context,
                const Duration(milliseconds: 450),
              ),
              curve: Curves.easeOutCubic,
              child: _SplashScreen(
                onAnimationDone: () {
                  if (mounted) setState(() => _animationDone = true);
                },
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _SplashScreen extends StatefulWidget {
  const _SplashScreen({required this.onAnimationDone});

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
      backgroundColor: AppColors.navy,
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
              const SizedBox(height: 48),
              // Círculo de carga desde el inicio, mientras todo se prepara.
              const SizedBox(
                width: 26,
                height: 26,
                child: CircularProgressIndicator(
                  strokeWidth: 2.6,
                  color: AppColors.accent,
                  backgroundColor: Color(0x24FFFFFF),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
