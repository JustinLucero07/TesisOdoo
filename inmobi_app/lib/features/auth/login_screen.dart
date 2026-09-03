import 'dart:math' as math;
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../../core/api/odoo_exception.dart';
import '../../core/theme/app_theme.dart';
import '../home/home_shell.dart';
import 'auth_service.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen>
    with TickerProviderStateMixin {
  final _formKey = GlobalKey<FormState>();
  final _loginCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _loginFocus = FocusNode();
  final _passwordFocus = FocusNode();

  bool _loading = false;
  bool _obscurePassword = true;
  String? _error;

  late final AnimationController _entranceCtrl;
  late final Animation<double> _formFadeAnim;
  late final Animation<Offset> _formSlideAnim;

  late final AnimationController _ambientCtrl;

  @override
  void initState() {
    super.initState();
    _prefill();

    // Animación de entrada general secuenciada
    _entranceCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1600),
    );

    _formFadeAnim = CurvedAnimation(
      parent: _entranceCtrl,
      curve: const Interval(0.45, 1.0, curve: Curves.easeOut),
    );

    _formSlideAnim = Tween<Offset>(
      begin: const Offset(0, 0.15),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _entranceCtrl,
        curve: const Interval(0.45, 1.0, curve: Curves.easeOutCubic),
      ),
    );

    // Animación ambiental de fondo infinito
    _ambientCtrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 8),
    )..repeat(reverse: true);

    _entranceCtrl.forward();
  }

  @override
  void dispose() {
    _entranceCtrl.dispose();
    _ambientCtrl.dispose();
    _loginCtrl.dispose();
    _passwordCtrl.dispose();
    _loginFocus.dispose();
    _passwordFocus.dispose();
    super.dispose();
  }

  Future<void> _prefill() async {
    final remembered = await context.read<AuthService>().loadRememberedLogin();
    if (!mounted || remembered == null) return;
    setState(() => _loginCtrl.text = remembered);
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) {
      HapticFeedback.mediumImpact();
      return;
    }
    FocusScope.of(context).unfocus();
    setState(() {
      _loading = true;
      _error = null;
    });
    HapticFeedback.lightImpact();

    try {
      await context.read<AuthService>().login(
        login: _loginCtrl.text.trim(),
        password: _passwordCtrl.text,
      );
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        PageRouteBuilder(
          pageBuilder: (context, anim, secondaryAnim) => const HomeShell(),
          transitionsBuilder: (context, anim, secondaryAnim, child) =>
              FadeTransition(opacity: anim, child: child),
          transitionDuration: const Duration(milliseconds: 400),
        ),
      );
    } on OdooException catch (e) {
      HapticFeedback.heavyImpact();
      setState(() => _error = e.message);
    } catch (e) {
      HapticFeedback.heavyImpact();
      debugPrint('Login error: $e');
      setState(
        () => _error = kDebugMode
            ? 'Error de conexión:\n$e'
            : 'No se pudo iniciar sesión. Verifica tu conexión e intenta de nuevo.',
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colors = AppColors.of(context);
    final size = MediaQuery.sizeOf(context);

    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF0C0A1E) : const Color(0xFFF8FAFC),
      body: Stack(
        children: [
          // ── 1. Fondo Ambiental con Orbes Dinámicos ──
          Positioned.fill(
            child: AnimatedBuilder(
              animation: _ambientCtrl,
              builder: (context, _) {
                final t = _ambientCtrl.value;
                final offset1 = math.sin(t * 2 * math.pi) * 25;
                final offset2 = math.cos(t * 2 * math.pi) * 30;

                return Stack(
                  children: [
                    // Orbe 1: Navy Inmobi Superior
                    Positioned(
                      top: -80 + offset1,
                      right: -60 + offset2,
                      width: size.width * 0.85,
                      height: size.width * 0.85,
                      child: Container(
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: RadialGradient(
                            colors: [
                              (isDark ? const Color(0xFF28235D) : const Color(0xFF28235D))
                                  .withValues(alpha: isDark ? 0.35 : 0.12),
                              Colors.transparent,
                            ],
                          ),
                        ),
                      ),
                    ),
                    // Orbe 2: Acento Rojo Inmobi Lateral
                    Positioned(
                      bottom: size.height * 0.15 - offset2,
                      left: -80 - offset1,
                      width: size.width * 0.75,
                      height: size.width * 0.75,
                      child: Container(
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: RadialGradient(
                            colors: [
                              const Color(0xFFD81F26)
                                  .withValues(alpha: isDark ? 0.18 : 0.08),
                              Colors.transparent,
                            ],
                          ),
                        ),
                      ),
                    ),
                  ],
                );
              },
            ),
          ),

          // ── 2. Contenido del Formulario ──
          SafeArea(
            child: Center(
              child: SingleChildScrollView(
                physics: const BouncingScrollPhysics(),
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 430),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      // ── Logo Inmobi con Animación de Ensamblaje Geométrico ──
                      const _AssemblingInmobiLogo(),

                      const SizedBox(height: 18),

                      // Marca y Subtítulo
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            'INMOBI',
                            style: TextStyle(
                              fontSize: 28,
                              fontWeight: FontWeight.w900,
                              letterSpacing: 3,
                              color: isDark ? Colors.white : const Color(0xFF1B1740),
                            ),
                          ),
                          const SizedBox(width: 4),
                          Container(
                            width: 7,
                            height: 7,
                            decoration: const BoxDecoration(
                              color: Color(0xFFD81F26),
                              shape: BoxShape.circle,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 4,
                        ),
                        decoration: BoxDecoration(
                          color: const Color(0xFF28235D)
                              .withValues(alpha: isDark ? 0.25 : 0.08),
                          borderRadius: BorderRadius.circular(100),
                          border: Border.all(
                            color: const Color(0xFF28235D).withValues(alpha: 0.15),
                          ),
                        ),
                        child: Text(
                          'PORTAL EJECUTIVO DE ASESORES',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 1.1,
                            color: isDark
                                ? const Color(0xFF9E96E6)
                                : const Color(0xFF28235D),
                          ),
                        ),
                      ),

                      const SizedBox(height: 28),

                      // ── Formulario con Slide & Fade Animado ──
                      FadeTransition(
                        opacity: _formFadeAnim,
                        child: SlideTransition(
                          position: _formSlideAnim,
                          child: Container(
                            padding: const EdgeInsets.all(26),
                            decoration: BoxDecoration(
                              color: isDark
                                  ? const Color(0xFF161330)
                                  : Colors.white,
                              borderRadius: BorderRadius.circular(28),
                              border: Border.all(
                                color: isDark
                                    ? const Color(0xFF28244E)
                                    : const Color(0xFFE2E8F0),
                                width: 1.2,
                              ),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withValues(
                                    alpha: isDark ? 0.35 : 0.06,
                                  ),
                                  blurRadius: 30,
                                  offset: const Offset(0, 10),
                                ),
                              ],
                            ),
                            child: Form(
                              key: _formKey,
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.stretch,
                                children: [
                                  Text(
                                    'Bienvenido',
                                    style: TextStyle(
                                      fontSize: 20,
                                      fontWeight: FontWeight.w800,
                                      letterSpacing: -0.3,
                                      color: isDark
                                          ? Colors.white
                                          : const Color(0xFF0F172A),
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    'Ingresa tus credenciales autorizadas de Inmobi',
                                    style: TextStyle(
                                      fontSize: 13,
                                      color: isDark
                                          ? const Color(0xFF94A3B8)
                                          : const Color(0xFF64748B),
                                    ),
                                  ),
                                  const SizedBox(height: 22),

                                  // Mensaje de Error
                                  if (_error != null) ...[
                                    Container(
                                      padding: const EdgeInsets.all(12),
                                      decoration: BoxDecoration(
                                        color: const Color(0xFFFEF2F2),
                                        borderRadius: BorderRadius.circular(14),
                                        border: Border.all(
                                          color: const Color(0xFFFCA5A5),
                                        ),
                                      ),
                                      child: Row(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          const Icon(
                                            Icons.error_outline_rounded,
                                            size: 18,
                                            color: Color(0xFFD81F26),
                                          ),
                                          const SizedBox(width: 8),
                                          Expanded(
                                            child: Text(
                                              _error!,
                                              style: const TextStyle(
                                                fontSize: 12.5,
                                                color: Color(0xFFD81F26),
                                                fontWeight: FontWeight.w600,
                                              ),
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                    const SizedBox(height: 18),
                                  ],

                                  // Campo Usuario
                                  TextFormField(
                                    controller: _loginCtrl,
                                    focusNode: _loginFocus,
                                    keyboardType: TextInputType.emailAddress,
                                    textInputAction: TextInputAction.next,
                                    style: const TextStyle(
                                      fontWeight: FontWeight.w600,
                                      fontSize: 14.5,
                                    ),
                                    decoration: InputDecoration(
                                      labelText: 'Usuario / Correo Odoo',
                                      labelStyle: TextStyle(
                                        color: isDark
                                            ? const Color(0xFF94A3B8)
                                            : const Color(0xFF64748B),
                                        fontSize: 13.5,
                                      ),
                                      prefixIcon: const Icon(
                                        Icons.person_outline_rounded,
                                        size: 20,
                                        color: Color(0xFF28235D),
                                      ),
                                      filled: true,
                                      fillColor: isDark
                                          ? const Color(0xFF0C0A1E)
                                          : const Color(0xFFF8FAFC),
                                      enabledBorder: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(16),
                                        borderSide: BorderSide(
                                          color: isDark
                                              ? const Color(0xFF28244E)
                                              : const Color(0xFFE2E8F0),
                                        ),
                                      ),
                                      focusedBorder: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(16),
                                        borderSide: const BorderSide(
                                          color: Color(0xFF28235D),
                                          width: 2,
                                        ),
                                      ),
                                    ),
                                    validator: (v) => (v == null || v.trim().isEmpty)
                                        ? 'Ingresa tu usuario de Odoo'
                                        : null,
                                  ),
                                  const SizedBox(height: 16),

                                  // Campo Contraseña
                                  TextFormField(
                                    controller: _passwordCtrl,
                                    focusNode: _passwordFocus,
                                    obscureText: _obscurePassword,
                                    textInputAction: TextInputAction.done,
                                    onFieldSubmitted: (_) => _submit(),
                                    style: const TextStyle(
                                      fontWeight: FontWeight.w600,
                                      fontSize: 14.5,
                                    ),
                                    decoration: InputDecoration(
                                      labelText: 'Contraseña',
                                      labelStyle: TextStyle(
                                        color: isDark
                                            ? const Color(0xFF94A3B8)
                                            : const Color(0xFF64748B),
                                        fontSize: 13.5,
                                      ),
                                      prefixIcon: const Icon(
                                        Icons.lock_outline_rounded,
                                        size: 20,
                                        color: Color(0xFF28235D),
                                      ),
                                      suffixIcon: IconButton(
                                        icon: AnimatedSwitcher(
                                          duration: const Duration(milliseconds: 200),
                                          child: Icon(
                                            _obscurePassword
                                                ? Icons.visibility_outlined
                                                : Icons.visibility_off_outlined,
                                            key: ValueKey(_obscurePassword),
                                            size: 20,
                                            color: const Color(0xFF94A3B8),
                                          ),
                                        ),
                                        onPressed: () {
                                          HapticFeedback.selectionClick();
                                          setState(
                                            () => _obscurePassword =
                                                !_obscurePassword,
                                          );
                                        },
                                      ),
                                      filled: true,
                                      fillColor: isDark
                                          ? const Color(0xFF0C0A1E)
                                          : const Color(0xFFF8FAFC),
                                      enabledBorder: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(16),
                                        borderSide: BorderSide(
                                          color: isDark
                                              ? const Color(0xFF28244E)
                                              : const Color(0xFFE2E8F0),
                                        ),
                                      ),
                                      focusedBorder: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(16),
                                        borderSide: const BorderSide(
                                          color: Color(0xFF28235D),
                                          width: 2,
                                        ),
                                      ),
                                    ),
                                    validator: (v) => (v == null || v.isEmpty)
                                        ? 'Ingresa tu contraseña'
                                        : null,
                                  ),
                                  const SizedBox(height: 24),

                                  // Botón Iniciar Sesión con Gradiente Inmobi
                                  SizedBox(
                                    height: 52,
                                    child: DecoratedBox(
                                      decoration: BoxDecoration(
                                        gradient: const LinearGradient(
                                          colors: [
                                            Color(0xFF28235D),
                                            Color(0xFF1B1740),
                                          ],
                                          begin: Alignment.topLeft,
                                          end: Alignment.bottomRight,
                                        ),
                                        borderRadius: BorderRadius.circular(16),
                                        boxShadow: [
                                          BoxShadow(
                                            color: const Color(0xFF28235D)
                                                .withValues(alpha: 0.35),
                                            blurRadius: 18,
                                            offset: const Offset(0, 6),
                                          ),
                                        ],
                                      ),
                                      child: ElevatedButton(
                                        onPressed: _loading ? null : _submit,
                                        style: ElevatedButton.styleFrom(
                                          backgroundColor: Colors.transparent,
                                          shadowColor: Colors.transparent,
                                          foregroundColor: Colors.white,
                                          shape: RoundedRectangleBorder(
                                            borderRadius: BorderRadius.circular(16),
                                          ),
                                        ),
                                        child: _loading
                                            ? const SizedBox(
                                                height: 22,
                                                width: 22,
                                                child: CircularProgressIndicator(
                                                  strokeWidth: 2.4,
                                                  color: Colors.white,
                                                ),
                                              )
                                            : const Row(
                                                mainAxisAlignment:
                                                    MainAxisAlignment.center,
                                                children: [
                                                  Text(
                                                    'Ingresar al Sistema',
                                                    style: TextStyle(
                                                      fontSize: 15.5,
                                                      fontWeight: FontWeight.w800,
                                                      letterSpacing: 0.3,
                                                    ),
                                                  ),
                                                  SizedBox(width: 8),
                                                  Icon(
                                                    Icons.arrow_forward_rounded,
                                                    size: 18,
                                                  ),
                                                ],
                                              ),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ),

                      const SizedBox(height: 26),

                      // ── Pie con Credenciales y Seguridad ──
                      FadeTransition(
                        opacity: _formFadeAnim,
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Container(
                              padding: const EdgeInsets.all(4),
                              decoration: BoxDecoration(
                                color: colors.success.withValues(alpha: 0.12),
                                shape: BoxShape.circle,
                              ),
                              child: Icon(
                                Icons.shield_rounded,
                                size: 14,
                                color: colors.success,
                              ),
                            ),
                            const SizedBox(width: 8),
                            Text(
                              'Conexión Segura y Encriptada · Inmobi',
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: isDark
                                    ? const Color(0xFF64748B)
                                    : const Color(0xFF94A3B8),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Widget con animación de ensamblaje geométrico de figuras para armar el logo de Inmobi
class _AssemblingInmobiLogo extends StatefulWidget {
  const _AssemblingInmobiLogo();

  @override
  State<_AssemblingInmobiLogo> createState() => _AssemblingInmobiLogoState();
}

class _AssemblingInmobiLogoState extends State<_AssemblingInmobiLogo>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  // Animaciones de las piezas geométricas
  late final Animation<Offset> _topRoofSlide;
  late final Animation<double> _topRoofRotate;
  late final Animation<Offset> _leftPillarSlide;
  late final Animation<Offset> _rightPillarSlide;
  late final Animation<double> _coreScale;

  // Animación del destello y ensamble final
  late final Animation<double> _finalBadgeScale;
  late final Animation<double> _flashAuraOpacity;
  late final Animation<double> _piecesFadeOut;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );

    // 1. Techo / Chevron rojo vuela desde arriba girando
    _topRoofSlide = Tween<Offset>(
      begin: const Offset(0.0, -1.8),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _controller,
        curve: const Interval(0.0, 0.55, curve: Curves.easeOutBack),
      ),
    );

    _topRoofRotate = Tween<double>(
      begin: -0.4,
      end: 0.0,
    ).animate(
      CurvedAnimation(
        parent: _controller,
        curve: const Interval(0.0, 0.55, curve: Curves.easeOutCubic),
      ),
    );

    // 2. Columna izquierda Navy entra desde la izquierda
    _leftPillarSlide = Tween<Offset>(
      begin: const Offset(-2.0, 0.6),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _controller,
        curve: const Interval(0.1, 0.60, curve: Curves.easeOutBack),
      ),
    );

    // 3. Columna derecha entra desde la derecha
    _rightPillarSlide = Tween<Offset>(
      begin: const Offset(2.0, 0.6),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _controller,
        curve: const Interval(0.15, 0.65, curve: Curves.easeOutBack),
      ),
    );

    // 4. Bloque central arquitectónico escala desde el centro
    _coreScale = CurvedAnimation(
      parent: _controller,
      curve: const Interval(0.2, 0.70, curve: Curves.elasticOut),
    );

    // 5. Destello / Resplandor cuando encajan las piezas
    _flashAuraOpacity = TweenSequence<double>([
      TweenSequenceItem(tween: Tween(begin: 0.0, end: 1.0), weight: 40),
      TweenSequenceItem(tween: Tween(begin: 1.0, end: 0.0), weight: 60),
    ]).animate(
      CurvedAnimation(
        parent: _controller,
        curve: const Interval(0.58, 0.90, curve: Curves.easeOut),
      ),
    );

    // 6. Fusión en el logo definitivo
    _piecesFadeOut = Tween<double>(begin: 1.0, end: 0.0).animate(
      CurvedAnimation(
        parent: _controller,
        curve: const Interval(0.65, 0.85, curve: Curves.easeInOut),
      ),
    );

    _finalBadgeScale = Tween<double>(begin: 0.82, end: 1.0).animate(
      CurvedAnimation(
        parent: _controller,
        curve: const Interval(0.65, 1.0, curve: Curves.easeOutBack),
      ),
    );

    _controller.forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _replay() {
    HapticFeedback.selectionClick();
    _controller.reset();
    _controller.forward();
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: _replay,
      child: AnimatedBuilder(
        animation: _controller,
        builder: (context, _) {
          return SizedBox(
            width: 140,
            height: 140,
            child: Stack(
              alignment: Alignment.center,
              children: [
                // Resplandor de Aura tras el ensamblaje
                Opacity(
                  opacity: _flashAuraOpacity.value,
                  child: Container(
                    width: 136,
                    height: 136,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: const Color(0xFFD81F26).withValues(alpha: 0.6),
                          blurRadius: 40,
                          spreadRadius: 10,
                        ),
                        BoxShadow(
                          color: const Color(0xFF28235D).withValues(alpha: 0.8),
                          blurRadius: 46,
                          spreadRadius: 12,
                        ),
                      ],
                    ),
                  ),
                ),

                // ── Piezas Geométricas en Movimiento (Se Desvanecen al Armarse) ──
                if (_piecesFadeOut.value > 0)
                  Opacity(
                    opacity: _piecesFadeOut.value,
                    child: SizedBox(
                      width: 110,
                      height: 110,
                      child: Stack(
                        alignment: Alignment.center,
                        children: [
                          // Pieza 1: Techo Rojo Triangular / Chevron
                          SlideTransition(
                            position: _topRoofSlide,
                            child: RotationTransition(
                              turns: _topRoofRotate,
                              child: Align(
                                alignment: Alignment.topCenter,
                                child: Container(
                                  width: 60,
                                  height: 28,
                                  decoration: BoxDecoration(
                                    color: const Color(0xFFD81F26),
                                    borderRadius: const BorderRadius.only(
                                      topLeft: Radius.circular(10),
                                      topRight: Radius.circular(10),
                                      bottomLeft: Radius.circular(6),
                                      bottomRight: Radius.circular(6),
                                    ),
                                    boxShadow: [
                                      BoxShadow(
                                        color: const Color(0xFFD81F26)
                                            .withValues(alpha: 0.4),
                                        blurRadius: 12,
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                          ),

                          // Pieza 2: Pilar Izquierdo Navy
                          SlideTransition(
                            position: _leftPillarSlide,
                            child: Align(
                              alignment: Alignment.bottomLeft,
                              child: Container(
                                width: 30,
                                height: 64,
                                decoration: BoxDecoration(
                                  color: const Color(0xFF28235D),
                                  borderRadius: BorderRadius.circular(10),
                                  boxShadow: [
                                    BoxShadow(
                                      color: const Color(0xFF28235D)
                                          .withValues(alpha: 0.4),
                                      blurRadius: 12,
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),

                          // Pieza 3: Pilar Derecho Navy Profundo
                          SlideTransition(
                            position: _rightPillarSlide,
                            child: Align(
                              alignment: Alignment.bottomRight,
                              child: Container(
                                width: 30,
                                height: 64,
                                decoration: BoxDecoration(
                                  color: const Color(0xFF1B1740),
                                  borderRadius: BorderRadius.circular(10),
                                  boxShadow: [
                                    BoxShadow(
                                      color: const Color(0xFF1B1740)
                                          .withValues(alpha: 0.4),
                                      blurRadius: 12,
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),

                          // Pieza 4: Núcleo Central
                          ScaleTransition(
                            scale: _coreScale,
                            child: Align(
                              alignment: Alignment.center,
                              child: Container(
                                width: 36,
                                height: 36,
                                decoration: BoxDecoration(
                                  color: const Color(0xFF3F3787),
                                  borderRadius: BorderRadius.circular(8),
                                  border: Border.all(
                                    color: Colors.white.withValues(alpha: 0.5),
                                    width: 2,
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),

                // ── Logo Unificado Final con Escala Grande y Halo ──
                if (_controller.value >= 0.6)
                  ScaleTransition(
                    scale: _finalBadgeScale,
                    child: Container(
                      width: 125,
                      height: 125,
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [Color(0xFF28235D), Color(0xFF18143C)],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        borderRadius: BorderRadius.circular(32),
                        border: Border.all(
                          color: Colors.white.withValues(alpha: 0.22),
                          width: 2,
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: const Color(0xFF28235D).withValues(alpha: 0.45),
                            blurRadius: 32,
                            offset: const Offset(0, 12),
                            spreadRadius: 3,
                          ),
                          BoxShadow(
                            color: const Color(0xFFD81F26).withValues(alpha: 0.3),
                            blurRadius: 20,
                            offset: const Offset(4, 6),
                          ),
                        ],
                      ),
                      child: Image.asset(
                        'assets/branding/logo_white.png',
                        fit: BoxFit.contain,
                      ),
                    ),
                  ),
              ],
            ),
          );
        },
      ),
    );
  }
}
