import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/message_model.dart';

class ChatNotifier extends StateNotifier<List<Message>> {
  ChatNotifier() : super([]);

  void addMessage(Message message) {
    state = [...state, message];
  }

  void clear() {
    state = [];
  }
}

final chatProvider = StateNotifierProvider<ChatNotifier, List<Message>>((ref) {
  return ChatNotifier();
});
