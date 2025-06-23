import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../widgets/message_bubble.dart';
import '../widgets/message_composer.dart';
import '../models/message_model.dart';
import '../providers/chat_provider.dart';
import '../api/pegasus_api_client.dart';
import '../services/voice_service.dart';

class ChatScreen extends ConsumerWidget {
  const ChatScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final messages = ref.watch(chatProvider);
    final controller = ScrollController();
    final api = PegasusApiClient(baseUrl: 'http://localhost:8000');
    final voice = VoiceService();

    void addMessage(String text, bool isUser) {
      ref.read(chatProvider.notifier).addMessage(Message(text: text, isUser: isUser));
      controller.animateTo(
        controller.position.maxScrollExtent + 60,
        duration: const Duration(milliseconds: 200),
        curve: Curves.easeOut,
      );
    }
    Future<void> sendMessage(String text) async {
      addMessage(text, true);
      try {
        final reply = await api.sendMessage(text);
        addMessage(reply, false);
        await voice.speak(reply);
      } catch (e) {
        addMessage('Error: $e', false);
      }
    }

    

    return Scaffold(
      appBar: AppBar(title: const Text('Pegasus Chat')),
      body: Column(
        children: [
          Expanded(
            child: ListView(
              controller: controller,
              children: [
                for (final msg in messages)
                  MessageBubble(text: msg.text, isUser: msg.isUser),
              ],
            ),
          ),
          MessageComposer(onSend: sendMessage),
        ],
      ),
    );
  }
}
