import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/physics.dart';
import 'package:flutter/services.dart';

import '../theme/app_motion.dart';

class PressableScale extends StatefulWidget {
  final Widget child;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;

  final double scale;

  final bool haptic;

  const PressableScale({
    super.key,
    required this.child,
    this.onTap,
    this.onLongPress,
    this.scale = 0.97,
    this.haptic = false,
  });

  @override
  State<PressableScale> createState() => _PressableScaleState();
}

class _PressableScaleState extends State<PressableScale>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl = AnimationController(
    vsync: this,
    duration: AppMotion.fast,
    value: 0,
  );

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  void _press() {
    if (AppMotion.reduced(context)) return;
    _ctrl.animateWith(
      SpringSimulation(AppMotion.springSnappy, _ctrl.value, 1, 0),
    );
  }

  void _release() {
    if (AppMotion.reduced(context)) return;

    _ctrl.animateWith(SpringSimulation(AppMotion.spring, _ctrl.value, 0, 0));
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTapDown: widget.onTap == null ? null : (_) => _press(),
      onTapCancel: widget.onTap == null ? null : _release,
      onTapUp: widget.onTap == null ? null : (_) => _release(),
      onTap: widget.onTap == null
          ? null
          : () {
              if (widget.haptic) HapticFeedback.selectionClick();
              widget.onTap!();
            },
      onLongPress: widget.onLongPress,
      child: AnimatedBuilder(
        animation: _ctrl,
        builder: (context, child) => Transform.scale(
          scale: 1 - (1 - widget.scale) * _ctrl.value,
          child: child,
        ),
        child: widget.child,
      ),
    );
  }
}

class FadeSlideIn extends StatefulWidget {
  final Widget child;
  final int index;
  final double offset;
  final Duration delayStep;

  const FadeSlideIn({
    super.key,
    required this.child,
    this.index = 0,
    this.offset = 16,
    this.delayStep = const Duration(milliseconds: 45),
  });

  @override
  State<FadeSlideIn> createState() => _FadeSlideInState();
}

class _FadeSlideInState extends State<FadeSlideIn>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl = AnimationController(
    vsync: this,
    duration: AppMotion.normal,
  );

  @override
  void initState() {
    super.initState();

    final steps = widget.index.clamp(0, 8);
    Future<void>.delayed(widget.delayStep * steps, () {
      if (mounted) _ctrl.forward();
    });
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (AppMotion.reduced(context)) return widget.child;

    final curved = CurvedAnimation(parent: _ctrl, curve: AppMotion.curve);
    return AnimatedBuilder(
      animation: curved,
      builder: (context, child) => Opacity(
        opacity: curved.value,
        child: Transform.translate(
          offset: Offset(0, widget.offset * (1 - curved.value)),
          child: child,
        ),
      ),
      child: widget.child,
    );
  }
}

class Materialize extends StatefulWidget {
  final Widget child;
  final Duration duration;

  const Materialize({
    super.key,
    required this.child,
    this.duration = AppMotion.normal,
  });

  @override
  State<Materialize> createState() => _MaterializeState();
}

class _MaterializeState extends State<Materialize>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl = AnimationController(
    vsync: this,
    duration: widget.duration,
  )..forward();

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (AppMotion.reduced(context)) return widget.child;

    final curved = CurvedAnimation(parent: _ctrl, curve: AppMotion.curve);
    return AnimatedBuilder(
      animation: curved,
      builder: (context, child) {
        final t = curved.value;
        return Opacity(
          opacity: t,
          child: Transform.scale(
            scale: 0.94 + 0.06 * t,
            child: ImageFiltered(
              enabled: t < 0.99,
              imageFilter: ImageFilter.blur(
                sigmaX: 8 * (1 - t),
                sigmaY: 8 * (1 - t),
                tileMode: TileMode.decal,
              ),
              child: child,
            ),
          ),
        );
      },
      child: widget.child,
    );
  }
}

class AppPageRoute<T> extends PageRouteBuilder<T> {
  AppPageRoute({required WidgetBuilder builder, super.settings})
    : super(
        transitionDuration: AppMotion.normal,
        reverseTransitionDuration: AppMotion.fast,
        pageBuilder: (context, _, _) => builder(context),
        transitionsBuilder: (context, animation, secondary, child) {
          if (AppMotion.reduced(context)) {
            return FadeTransition(opacity: animation, child: child);
          }
          final entering = CurvedAnimation(
            parent: animation,
            curve: AppMotion.curve,
            reverseCurve: AppMotion.curveExit,
          );

          final leaving = CurvedAnimation(
            parent: secondary,
            curve: AppMotion.curve,
          );
          return SlideTransition(
            position: Tween(
              begin: const Offset(0.06, 0),
              end: Offset.zero,
            ).animate(entering),
            child: FadeTransition(
              opacity: entering,
              child: SlideTransition(
                position: Tween(
                  begin: Offset.zero,
                  end: const Offset(-0.04, 0),
                ).animate(leaving),
                child: child,
              ),
            ),
          );
        },
      );
}
