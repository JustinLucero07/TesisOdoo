import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../auth/auth_service.dart';
import 'chat_service.dart';

class _ChatMessage {
  String text;
  final bool isUser;
  bool isStreaming;
  _ChatMessage({
    required this.text,
    required this.isUser,
    this.isStreaming = false,
  });
}

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  late final ChatService _service;
  final _inputCtrl = TextEditingController();
  final _scrollCtrl = ScrollController();
  final List<_ChatMessage> _messages = [];
  String? _status;
  bool _sending = false;

  @override
  void initState() {
    super.initState();
    _service = ChatService(context.read<AuthService>().odoo);
  }

  Future<void> _send() async {
    final text = _inputCtrl.text.trim();
    if (text.isEmpty || _sending) return;
    _inputCtrl.clear();

    setState(() {
      _messages.add(_ChatMessage(text: text, isUser: true));
      final reply = _ChatMessage(text: '', isUser: false, isStreaming: true);
      _messages.add(reply);
      _sending = true;
      _status = null;
    });
    _scrollToEnd();

    final replyMsg = _messages.last;
    try {
      await for (final event in _service.sendMessage(text)) {
        if (event is ChatStatusEvent) {
          setState(() => _status = event.status);
        } else if (event is ChatTextEvent) {
          setState(() {
            _status = null;
            replyMsg.text += event.text;
          });
          _scrollToEnd();
        } else if (event is ChatErrorEvent) {
          setState(() => replyMsg.text = 'Error: ${event.error}');
        } else if (event is ChatDoneEvent) {
          setState(() => replyMsg.isStreaming = false);
        }
      }
    } catch (e) {
      setState(() {
        replyMsg.text = 'No se pudo contactar al agente. Revisa tu conexión.';
        replyMsg.isStreaming = false;
      });
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  void _scrollToEnd() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollCtrl.hasClients) return;
      _scrollCtrl.animateTo(
        _scrollCtrl.position.maxScrollExtent,
        duration: const Duration(milliseconds: 200),
        curve: Curves.easeOut,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.of(context);
    return Column(
      children: [
        Expanded(
          child: _messages.isEmpty
              ? const _EmptyChatHint()
              : ListView.builder(
                  controller: _scrollCtrl,
                  padding: const EdgeInsets.all(14),
                  itemCount: _messages.length,
                  itemBuilder: (context, i) =>
                      _MessageBubble(message: _messages[i]),
                ),
        ),
        if (_status != null)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Align(
              alignment: Alignment.centerLeft,
              child: Text(
                _status!,
                style: TextStyle(color: colors.muted, fontSize: 12.5),
              ),
            ),
          ),
        SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _inputCtrl,
                    minLines: 1,
                    maxLines: 4,
                    decoration: const InputDecoration(
                      hintText: 'Pregúntale al agente...',
                    ),
                    onSubmitted: (_) => _send(),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton.filled(
                  onPressed: _sending ? null : _send,
                  icon: const Icon(Icons.send),
                  style: IconButton.styleFrom(
                    backgroundColor: colors.navy,
                    foregroundColor: Colors.white,
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _EmptyChatHint extends StatelessWidget {
  const _EmptyChatHint();

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.smart_toy_outlined, size: 48, color: colors.muted),
            const SizedBox(height: 12),
            Text(
              'El mismo agente del ERP, ahora desde el celular.\nPregunta por propiedades, leads o reportes.',
              textAlign: TextAlign.center,
              style: TextStyle(color: colors.muted),
            ),
          ],
        ),
      ),
    );
  }
}

class _MessageBubble extends StatelessWidget {
  final _ChatMessage message;
  const _MessageBubble({required this.message});

  @override
  Widget build(BuildContext context) {
    final colors = AppColors.of(context);
    final isUser = message.isUser;
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.78,
        ),
        decoration: BoxDecoration(
          color: isUser ? colors.navy : Colors.white,
          border: isUser ? null : Border.all(color: colors.line),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Text(
          message.text.isEmpty && message.isStreaming ? '...' : message.text,
          style: TextStyle(
            color: isUser ? Colors.white : colors.ink,
            fontSize: 14.5,
          ),
        ),
      ),
    );
  }
}
