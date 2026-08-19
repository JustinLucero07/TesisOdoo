import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';

import '../../core/api/odoo_client.dart';

/// Evento recibido del endpoint de streaming del agente de IA
/// (`/estate_ai/chat/stream`, el mismo que usa el chat flotante del ERP).
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

/// Habla con el agente de IA ya existente en el ERP (Gemini/OpenAI por
/// detrás, tool-calling, RAG, etc.) — la app solo consume el mismo endpoint
/// SSE que usa el chat flotante web, no reimplementa nada del agente.
class ChatService {
  final OdooClient odoo;
  ChatService(this.odoo);

  /// Envía un mensaje y devuelve un stream de eventos según van llegando
  /// (estado del agente, fragmentos de texto, error, o fin de respuesta).
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
      // Los eventos SSE vienen separados por una línea en blanco.
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
          } catch (_) {
            // Línea SSE no-JSON — se ignora en vez de romper el stream.
          }
        }
      }
    }
  }
}
