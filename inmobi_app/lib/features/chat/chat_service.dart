import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';

import '../../core/api/odoo_client.dart';

sealed class ChatStreamEvent {}

class ChatStatusEvent extends ChatStreamEvent {
  final String status;
  ChatStatusEvent(this.status);
}

class ChatTextEvent extends ChatStreamEvent {
  final String text;
  ChatTextEvent(this.text);
}

class ChatErrorEvent extends ChatStreamEvent {
  final String error;
  ChatErrorEvent(this.error);
}

class ChatDoneEvent extends ChatStreamEvent {}

class ChatService {
  final OdooClient odoo;
  ChatService(this.odoo);

  Stream<ChatStreamEvent> sendMessage(
    String message, {
    String? sessionId,
  }) async* {
    final response = await odoo.client.post(
      '/estate_ai/chat/stream',
      data: {
        'message': message,
        if (sessionId != null) 'session_id': sessionId,
      },
      options: Options(
        responseType: ResponseType.stream,
        headers: {'Accept': 'text/event-stream'},
      ),
    );

    final stream = (response.data as ResponseBody).stream;
    var buffer = '';

    await for (final chunk in stream) {
      buffer += utf8.decode(chunk, allowMalformed: true);

      while (buffer.contains('\n\n')) {
        final idx = buffer.indexOf('\n\n');
        final rawEvent = buffer.substring(0, idx);
        buffer = buffer.substring(idx + 2);

        for (final line in rawEvent.split('\n')) {
          if (!line.startsWith('data:')) continue;
          final payload = line.substring(5).trim();
          if (payload == '[DONE]') {
            yield ChatDoneEvent();
            continue;
          }
          try {
            final json = jsonDecode(payload) as Map<String, dynamic>;
            if (json.containsKey('text')) {
              yield ChatTextEvent(json['text'] as String);
            } else if (json.containsKey('status')) {
              yield ChatStatusEvent(json['status'] as String);
            } else if (json.containsKey('error')) {
              yield ChatErrorEvent(json['error'] as String);
            }
          } catch (_) {}
        }
      }
    }
  }
}
